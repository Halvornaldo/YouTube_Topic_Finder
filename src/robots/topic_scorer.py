"""
Robot 1.5: Topic Scorer

Evaluates seed topics using LLM (Gemini) to score their monetization potential.
This robot sits between Robot 1 (Horizon Scanner) and Robot 2 (SERP Scraper),
filtering topics based on profitability rather than just social engagement.
"""

import logging
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from src.models.seed_topic import SeedTopic
from src.services.llm_service import LLMService, LLMServiceError
from src.services.config_manager import ConfigManager
from src.config.settings import settings

logger = logging.getLogger(__name__)


class TopicScorer:
    """
    Robot 1.5: Topic Scorer

    Uses LLM to evaluate topics for monetization potential.
    Scores topics 0-100 based on:
    - High-CPM niche potential
    - Tier-1 audience appeal
    - Commercial intent
    - Advertiser-friendliness
    - Searchability on YouTube

    Topics scoring 0 are auto-rejected.
    Final score is weighted combination of raw_score (Robot 1) and llm_score.
    """

    def __init__(self, db_session: Session):
        """
        Initialize Topic Scorer.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.config_manager = ConfigManager(db_session)
        self.llm_service: Optional[LLMService] = None

    async def run(
        self,
        niche: Optional[str] = None,
        batch_size: Optional[int] = None,
        force_rescore: bool = False
    ) -> Dict:
        """
        Score unscored topics using LLM.

        Args:
            niche: Optional niche filter (defaults to all niches)
            batch_size: Number of topics to score (defaults to config)
            force_rescore: Re-score already scored topics

        Returns:
            Dict with summary of scoring results

        Raises:
            LLMServiceError: If LLM service cannot be initialized
        """
        logger.info(f"Starting Topic Scorer (Robot 1.5) - niche: {niche or 'all'}")

        # Load configuration
        config_snapshot = await self._load_config()
        batch_size = batch_size or config_snapshot.get("robot1_5_batch_size", 20)
        llm_weight = config_snapshot.get("robot1_5_llm_weight", 0.7)
        raw_weight = 1.0 - llm_weight
        min_llm_score = config_snapshot.get("robot1_5_min_llm_score", 60.0)
        llm_model = config_snapshot.get("robot1_5_llm_model", "gemini-2.0-flash-exp")

        # Initialize LLM service with API key and model from settings
        try:
            self.llm_service = LLMService(api_key=settings.GEMINI_API_KEY, model=llm_model)
            logger.info(f"LLM service initialized successfully with model: {llm_model}")
        except LLMServiceError as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise

        # Get unscored topics
        topics = self._get_unscored_topics(niche, batch_size, force_rescore)
        logger.info(f"Found {len(topics)} topics to score")

        if not topics:
            return {
                "topics_scored": 0,
                "topics_rejected": 0,
                "topics_accepted": 0,
                "message": "No topics to score"
            }

        # Score topics
        scored_count = 0
        rejected_count = 0
        accepted_count = 0
        errors = []

        for topic in topics:
            try:
                # Score topic with LLM
                result = await self.llm_service.score_topic(
                    topic=topic.topic,
                    source=topic.source.value,
                    niche=topic.niche,
                    raw_score=topic.trend_score or 0.0
                )

                # Calculate final score (weighted combination)
                raw_score = topic.trend_score or 0.0
                llm_score = result["score"]
                final_score = (raw_weight * raw_score) + (llm_weight * llm_score)

                # Update topic with LLM results
                topic.raw_score = raw_score
                topic.llm_score = llm_score
                topic.final_score = final_score
                topic.llm_reasoning = result["reasoning"]
                topic.profit_angle = result["profit_angle"]
                topic.scored_at = datetime.utcnow()
                topic.llm_provider = "gemini"

                # Auto-reject if LLM score is 0 or below minimum
                if llm_score == 0:
                    topic.status = "rejected"
                    rejected_count += 1
                    logger.info(f"Rejected (score 0): {topic.topic[:50]}...")
                elif llm_score < min_llm_score:
                    topic.status = "rejected"
                    rejected_count += 1
                    logger.info(f"Rejected (score {llm_score} < {min_llm_score}): {topic.topic[:50]}...")
                else:
                    topic.status = "scored"
                    accepted_count += 1
                    logger.info(f"Scored {llm_score}/100 (final: {final_score:.1f}): {topic.topic[:50]}...")

                scored_count += 1

                # Commit after each topic to avoid losing progress
                self.db.commit()

                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)

            except LLMServiceError as e:
                logger.error(f"Error scoring topic '{topic.topic[:50]}...': {e}")
                errors.append({"topic": topic.topic[:50], "error": str(e)})
                # Continue with next topic
                continue

        result_summary = {
            "topics_scored": scored_count,
            "topics_rejected": rejected_count,
            "topics_accepted": accepted_count,
            "llm_weight": llm_weight,
            "raw_weight": raw_weight,
            "min_llm_score": min_llm_score,
            "errors": errors
        }

        logger.info(f"Topic Scorer completed: {result_summary}")
        return result_summary

    async def _load_config(self) -> Dict:
        """Load configuration for Robot 1.5."""
        # Get individual settings using ConfigManager.get()
        config = {
            "robot1_5_batch_size": self.config_manager.get("robot1_5_batch_size", 20),
            "robot1_5_llm_weight": self.config_manager.get("robot1_5_llm_weight", 0.7),
            "robot1_5_min_llm_score": self.config_manager.get("robot1_5_min_llm_score", 60.0),
            "robot1_5_llm_model": self.config_manager.get("robot1_5_llm_model", "gemini-2.0-flash-exp")
        }

        logger.debug(f"Robot 1.5 configuration loaded: {config}")
        return config

    def _get_unscored_topics(
        self,
        niche: Optional[str],
        batch_size: int,
        force_rescore: bool
    ) -> List[SeedTopic]:
        """
        Get topics that need scoring.

        Args:
            niche: Optional niche filter
            batch_size: Number of topics to retrieve
            force_rescore: Re-score already scored topics

        Returns:
            List of SeedTopic objects
        """
        query = self.db.query(SeedTopic)

        # Filter by niche if specified
        if niche:
            query = query.filter(SeedTopic.niche == niche)

        # Filter by scoring status
        if force_rescore:
            # Re-score all topics
            pass
        else:
            # Only score unscored topics (status = pending OR llm_score IS NULL)
            query = query.filter(
                and_(
                    SeedTopic.status == "pending",
                    SeedTopic.llm_score.is_(None)
                )
            )

        # Order by creation date (oldest first)
        query = query.order_by(SeedTopic.created_at.asc())

        # Limit batch size
        query = query.limit(batch_size)

        return query.all()

    async def score_single_topic(self, topic_id: int) -> Dict:
        """
        Score a single topic by ID.

        Args:
            topic_id: ID of topic to score

        Returns:
            Dict with scoring results

        Raises:
            ValueError: If topic not found
            LLMServiceError: If scoring fails
        """
        topic = self.db.query(SeedTopic).filter(SeedTopic.id == topic_id).first()
        if not topic:
            raise ValueError(f"Topic {topic_id} not found")

        # Load config
        config_snapshot = await self._load_config()
        llm_weight = config_snapshot.get("robot1_5_llm_weight", 0.7)
        raw_weight = 1.0 - llm_weight
        llm_model = config_snapshot.get("robot1_5_llm_model", "gemini-2.0-flash-exp")

        # Initialize LLM service if needed
        if not self.llm_service:
            self.llm_service = LLMService(api_key=settings.GEMINI_API_KEY, model=llm_model)

        # Score topic
        result = await self.llm_service.score_topic(
            topic=topic.topic,
            source=topic.source.value,
            niche=topic.niche,
            raw_score=topic.trend_score or 0.0
        )

        # Calculate final score
        raw_score = topic.trend_score or 0.0
        llm_score = result["score"]
        final_score = (raw_weight * raw_score) + (llm_weight * llm_score)

        # Update topic
        topic.raw_score = raw_score
        topic.llm_score = llm_score
        topic.final_score = final_score
        topic.llm_reasoning = result["reasoning"]
        topic.profit_angle = result["profit_angle"]
        topic.scored_at = datetime.utcnow()
        topic.llm_provider = "gemini"
        topic.status = "rejected" if llm_score == 0 else "scored"

        self.db.commit()

        return {
            "topic_id": topic_id,
            "raw_score": raw_score,
            "llm_score": llm_score,
            "final_score": final_score,
            "status": topic.status,
            "reasoning": result["reasoning"],
            "profit_angle": result["profit_angle"]
        }
