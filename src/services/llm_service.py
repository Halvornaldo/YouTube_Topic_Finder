"""LLM Service for topic scoring using Gemini API."""

import logging
import json
import os
from typing import Dict, Optional
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""
    pass


class LLMRateLimitError(LLMServiceError):
    """Raised when rate limit is exceeded."""
    pass


class LLMResponseError(LLMServiceError):
    """Raised when LLM response is invalid."""
    pass


class LLMService:
    """
    Service for evaluating topics using LLM (Google Gemini).

    Implements the TrendConverter prompt to score topics based on
    monetization potential rather than social engagement metrics.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize LLM service.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Gemini model to use (default: gemini-2.0-flash-exp)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise LLMServiceError("GEMINI_API_KEY not provided and not found in environment")

        self.model_name = model

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )

        logger.info(f"LLM service initialized with model: {self.model_name}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(LLMRateLimitError),
        reraise=True
    )
    async def score_topic(
        self,
        topic: str,
        source: str,
        niche: str,
        raw_score: float,
        prompt_template: Optional[str] = None
    ) -> Dict:
        """
        Score a topic using LLM evaluation.

        Args:
            topic: The topic text
            source: Source of the topic (reddit, google_trends)
            niche: Niche category
            raw_score: Original score from Robot 1 (0-100)
            prompt_template: Custom prompt template (defaults to TrendConverter)

        Returns:
            Dict with keys: score, reasoning, profit_angle

        Raises:
            LLMRateLimitError: When rate limit is exceeded
            LLMResponseError: When response is invalid
            LLMServiceError: For other errors
        """
        try:
            # Use default TrendConverter prompt if not provided
            if not prompt_template:
                prompt_template = self._get_default_prompt()

            # Format prompt with topic data
            prompt = prompt_template.format(
                topic=topic,
                source=source,
                niche=niche,
                raw_score=raw_score
            )

            logger.debug(f"Sending topic to LLM: {topic[:50]}...")

            # Call Gemini API
            response = self.model.generate_content(prompt)

            # Extract text from response
            if not response or not response.text:
                raise LLMResponseError("Empty response from LLM")

            response_text = response.text.strip()
            logger.debug(f"LLM response: {response_text[:200]}...")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Validate result
            self._validate_result(result)

            logger.info(f"Topic scored: {topic[:50]}... => {result['score']}/100")
            return result

        except Exception as e:
            if "quota" in str(e).lower() or "rate limit" in str(e).lower():
                logger.error(f"Rate limit exceeded: {e}")
                raise LLMRateLimitError(f"Rate limit exceeded: {e}")
            elif isinstance(e, (LLMResponseError, LLMServiceError)):
                raise
            else:
                logger.error(f"Error scoring topic: {e}")
                raise LLMServiceError(f"Error scoring topic: {e}")

    def _parse_response(self, response_text: str) -> Dict:
        """
        Parse JSON response from LLM.

        Handles various response formats and extracts JSON.
        """
        # Try to find JSON in response (LLM might add explanation before/after)
        # Look for content between triple backticks or raw JSON
        json_str = response_text

        # Remove markdown code fences if present
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()

        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {json_str[:200]}")
            raise LLMResponseError(f"Invalid JSON response: {e}")

    def _validate_result(self, result: Dict) -> None:
        """Validate LLM response has required fields."""
        required_fields = ["score", "reasoning", "profit_angle"]
        missing = [f for f in required_fields if f not in result]

        if missing:
            raise LLMResponseError(f"Missing required fields: {missing}")

        # Validate score is in range
        score = result["score"]
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            raise LLMResponseError(f"Invalid score: {score} (must be 0-100)")

    def _get_default_prompt(self) -> str:
        """
        Get the default TrendConverter prompt.

        This is the prompt discussed with the user that focuses on
        monetization potential over social engagement metrics.
        """
        return """You are 'TrendConverter', an expert YouTube Monetization Strategist. You specialize in converting volatile, low-CPM social media trends into high-CPM, profitable YouTube content.

**Your Guiding Principle:** You are skeptical. You know that high social engagement (likes, shares, upvotes) does NOT equal high profit (RPM). Your job is to find the hidden business/profit angle.

**Your Task:** Evaluate this topic for income-generating potential:

Topic: "{topic}"
Source: {source}
Niche: {niche}
Social Score: {raw_score}/100 (based on {source} engagement)

**Your Analysis Must Prioritize:**

1. **High-CPM Niche Pivot**: Can this trend connect to high-value categories (Finance, Tech, Software, B2B, Real Estate, Health, Legal)?

2. **Tier-1 Audience Appeal**: Is this relevant to audiences in USA, UK, Canada, Australia?

3. **Commercial Intent**: Does it attract viewers looking to buy something or solve a business problem?

4. **Advertiser-Friendliness**: Is the angle 100% brand-safe? No controversial content.

5. **Searchability**: Will people actively search for this on YouTube (not just browse)?

**Scoring Rules:**

- Score 0: Reject if vague, spam, controversial, bot-generated, or zero profit potential
- Score 1-39: Low profit - viral/entertainment only, no commercial angle
- Score 40-69: Medium profit - some commercial potential but needs better angle
- Score 70-100: High profit - clear high-CPM niche, commercial intent, Tier-1 audience

**Required Output:** Return ONLY valid JSON:

{{
  "score": 85,
  "reasoning": "Contrast the Social Score with profit potential. Why does this topic score high/low for MONEY?",
  "profit_angle": "The High-CPM Video Title - How you'd pivot this for maximum profit"
}}

**Example:**
- Topic: "This AI tool is insane!!!" (Social Score: 95/100)
- Your Analysis: Score 15/100 - High social engagement but vague, no clear problem being solved, targets consumers not businesses. Low commercial intent.
- Profit Angle: "AI Automation Tool for Small Businesses: ROI Analysis & Implementation Guide"
"""

    async def test_connection(self) -> bool:
        """
        Test LLM API connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.model.generate_content("Test connection. Respond with 'OK'.")
            return bool(response and response.text)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_model_info(self) -> Dict:
        """Get information about current model configuration."""
        return {
            "model": self.model_name,
            "provider": "google_gemini",
            "configured": bool(self.api_key)
        }
