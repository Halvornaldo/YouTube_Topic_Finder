"""Robot 2: SERP Scraper - Discovers candidate YouTube videos from search results."""

import logging
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import time

from src.models.seed_topic import SeedTopic
from src.models.search_query import SearchQuery
from src.models.video import Video
from src.models.job_status import JobStatus
from src.services.config_manager import ConfigManager
from src.services.event_manager import (
    broadcast_job_started,
    broadcast_job_progress,
    broadcast_job_completed,
    broadcast_job_failed,
    broadcast_robot_status,
    broadcast_video_discovered
)

logger = logging.getLogger(__name__)


class SerpScraper:
    """
    Robot 2: SERP Scraper

    Discovers candidate YouTube videos by:
    - Taking unprocessed seed topics from Robot 1
    - Performing YouTube searches (Playwright + API fallback)
    - Extracting video metadata
    - Saving videos to database

    Integrated with:
    - ConfigManager for settings
    - JobStatus for progress tracking
    - EventManager for real-time updates
    """

    def __init__(self, db_session: Session):
        """
        Initialize SERP Scraper.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.config_manager = ConfigManager(db_session)
        self.playwright_browser = None
        self.playwright_context = None
        self.youtube_api_client = None
        self.job_id: Optional[int] = None

    async def run(self, niche_name: str, max_topics: Optional[int] = None) -> Dict:
        """
        Run the SERP Scraper for a specific niche.

        Args:
            niche_name: Name of the niche to process
            max_topics: Maximum number of topics to process (optional)

        Returns:
            Dict with scraping results
        """
        logger.info(f"Starting SERP Scraper for niche: {niche_name}")

        # Get max topics from ConfigManager if not specified
        if max_topics is None:
            max_topics = self.config_manager.get('robot2.max_topics_per_run', 10, 'robot2')

        # Get unprocessed seed topics for this niche
        stmt = select(SeedTopic).where(
            SeedTopic.niche == niche_name,
            SeedTopic.processed == 0
        ).order_by(SeedTopic.trend_score.desc()).limit(max_topics)

        seed_topics = self.db.execute(stmt).scalars().all()

        if not seed_topics:
            logger.warning(f"No unprocessed seed topics found for niche '{niche_name}'")
            return {
                "status": "completed",
                "message": "No unprocessed topics found",
                "niche": niche_name,
                "topics_processed": 0,
                "videos_found": 0
            }

        # Create job status record
        job = JobStatus(
            job_type='robot2',
            status='running',
            config_snapshot={
                'niche_name': niche_name,
                'max_topics': max_topics,
                'topics_found': len(seed_topics),
                'use_playwright': self.config_manager.get('robot2.use_playwright', True, 'robot2'),
                'api_fallback': self.config_manager.get('robot2.youtube_api_fallback', True, 'robot2')
            }
        )
        job.start()
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self.job_id = job.id

        try:
            # Broadcast job started event
            await broadcast_job_started(
                job_id=job.id,
                job_type='robot2',
                niche_name=niche_name,
                topics_count=len(seed_topics)
            )

            # Broadcast robot status
            await broadcast_robot_status(
                robot='robot2',
                status='running',
                niche=niche_name
            )

            # Update progress: Initializing
            job.update_progress(5, "Initializing scraper")
            self.db.commit()
            await broadcast_job_progress(job.id, 5, "Initializing scraper")

            # Initialize clients
            await self._init_clients()

            total_videos_found = 0
            topics_processed = 0

            # Process each seed topic
            for index, seed_topic in enumerate(seed_topics):
                try:
                    progress = 10 + int((index / len(seed_topics)) * 80)
                    job.update_progress(
                        progress,
                        f"Processing topic {index + 1}/{len(seed_topics)}: {seed_topic.topic[:50]}"
                    )
                    self.db.commit()
                    await broadcast_job_progress(
                        job.id,
                        progress,
                        f"Processing: {seed_topic.topic[:50]}"
                    )

                    logger.info(f"Processing topic: {seed_topic.topic}")

                    # Perform search
                    videos = await self._search_videos(seed_topic)
                    total_videos_found += len(videos)

                    # Mark topic as processed
                    seed_topic.processed = 1
                    seed_topic.processed_at = datetime.utcnow()
                    topics_processed += 1

                    self.db.commit()

                    # Rate limiting delay
                    delay = self.config_manager.get('robot2.delay_between_searches', 3, 'robot2')
                    if index < len(seed_topics) - 1:  # Don't delay after last topic
                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Error processing topic '{seed_topic.topic}': {e}", exc_info=True)
                    # Continue with next topic instead of failing entire job
                    continue

            # Cleanup clients
            await self._cleanup_clients()

            # Complete the job
            job.update_progress(100, "Completed")
            result_summary = {
                "topics_processed": topics_processed,
                "videos_found": total_videos_found,
                "niche": niche_name
            }
            job.complete(result_summary=result_summary)
            self.db.commit()

            logger.info(f"SERP Scraper completed. Processed {topics_processed} topics, found {total_videos_found} videos.")

            # Broadcast completion
            await broadcast_job_completed(
                job_id=job.id,
                result_summary=result_summary
            )

            await broadcast_robot_status(
                robot='robot2',
                status='idle',
                last_run_result=result_summary
            )

            return {
                "status": "completed",
                "job_id": job.id,
                "niche": niche_name,
                **result_summary
            }

        except Exception as e:
            logger.error(f"Error in SERP Scraper: {e}", exc_info=True)

            # Cleanup on error
            await self._cleanup_clients()

            # Mark job as failed
            if job:
                job.fail(error_message=str(e))
                self.db.commit()

                await broadcast_job_failed(
                    job_id=job.id,
                    error=str(e)
                )

                await broadcast_robot_status(
                    robot='robot2',
                    status='error',
                    error=str(e)
                )

            raise

    async def _init_clients(self):
        """Initialize Playwright browser and/or YouTube API client."""
        use_playwright = self.config_manager.get('robot2.use_playwright', True, 'robot2')

        if use_playwright:
            try:
                from playwright.async_api import async_playwright

                logger.info("Initializing Playwright browser...")
                self.playwright = await async_playwright().start()

                headless = self.config_manager.get('robot2.headless', True, 'robot2')
                user_agent = self.config_manager.get(
                    'robot2.user_agent',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'robot2'
                )

                self.playwright_browser = await self.playwright.chromium.launch(headless=headless)
                self.playwright_context = await self.playwright_browser.new_context(
                    user_agent=user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )

                logger.info("Playwright browser initialized successfully")
            except ImportError:
                logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
                self.playwright_browser = None
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {e}")
                self.playwright_browser = None

        # Initialize YouTube API client if fallback enabled
        api_fallback = self.config_manager.get('robot2.youtube_api_fallback', True, 'robot2')
        if api_fallback:
            try:
                from googleapiclient.discovery import build

                api_key = self.config_manager.get('youtube.api_key', None, 'api_keys')

                if api_key:
                    self.youtube_api_client = build('youtube', 'v3', developerKey=api_key)
                    logger.info("YouTube API client initialized")
                else:
                    logger.warning("YouTube API key not configured")
                    self.youtube_api_client = None
            except ImportError:
                logger.warning("google-api-python-client not installed. Install with: pip install google-api-python-client")
                self.youtube_api_client = None
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
                self.youtube_api_client = None

    async def _cleanup_clients(self):
        """Cleanup Playwright browser and API clients."""
        if self.playwright_context:
            try:
                await self.playwright_context.close()
            except Exception as e:
                logger.error(f"Error closing Playwright context: {e}")

        if self.playwright_browser:
            try:
                await self.playwright_browser.close()
            except Exception as e:
                logger.error(f"Error closing Playwright browser: {e}")

        if hasattr(self, 'playwright') and self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}")

    async def _search_videos(self, seed_topic: SeedTopic) -> List[Video]:
        """
        Search for videos for a given seed topic.

        Args:
            seed_topic: Seed topic to search for

        Returns:
            List of Video objects found
        """
        query_text = seed_topic.topic
        max_results = self.config_manager.get('robot2.max_videos_per_query', 20, 'robot2')

        # Create search query record
        search_query = SearchQuery(
            query_text=query_text,
            seed_topic_id=seed_topic.id,
            niche=seed_topic.niche,
            max_results=max_results
        )
        self.db.add(search_query)
        self.db.commit()
        self.db.refresh(search_query)

        start_time = time.time()
        videos_found = []

        try:
            # Try Playwright first
            if self.playwright_browser:
                logger.info(f"Attempting Playwright scrape for: {query_text}")
                videos_found = await self._scrape_with_playwright(query_text, max_results, search_query.id)
                search_query.search_method = 'playwright'

            # Fallback to API if Playwright failed or not available
            if not videos_found and self.youtube_api_client:
                logger.info(f"Attempting YouTube API search for: {query_text}")
                videos_found = await self._scrape_with_api(query_text, max_results, search_query.id)
                search_query.search_method = 'api'

            # Update search query with results
            execution_time = int(time.time() - start_time)
            search_query.execution_time_seconds = execution_time
            search_query.videos_scraped = len(videos_found)
            search_query.success = 1 if videos_found else 0

            if not videos_found:
                search_query.error_message = "No videos found by any method"

            self.db.commit()

            logger.info(f"Found {len(videos_found)} videos for query: {query_text}")
            return videos_found

        except Exception as e:
            logger.error(f"Error searching for videos: {e}", exc_info=True)

            # Update search query with error
            search_query.success = 0
            search_query.error_message = str(e)
            search_query.execution_time_seconds = int(time.time() - start_time)
            self.db.commit()

            return []

    async def _scrape_with_playwright(self, query: str, max_results: int, search_query_id: int) -> List[Video]:
        """
        Scrape YouTube search results using Playwright.

        Args:
            query: Search query
            max_results: Maximum number of videos to scrape
            search_query_id: ID of search query record

        Returns:
            List of Video objects
        """
        videos = []

        try:
            page = await self.playwright_context.new_page()

            # Navigate to YouTube search
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            await page.goto(search_url, wait_until='networkidle')

            # Wait for video elements to load
            await page.wait_for_selector('ytd-video-renderer', timeout=10000)

            # Extract video data
            video_elements = await page.query_selector_all('ytd-video-renderer')

            for index, element in enumerate(video_elements[:max_results]):
                try:
                    video_data = await self._extract_video_from_element(element, index + 1)
                    if video_data:
                        video = self._save_video(video_data, search_query_id)
                        if video:
                            videos.append(video)
                            # Broadcast video discovery event
                            await broadcast_video_discovered(
                                video_id=video.video_id,
                                title=video.title,
                                source='playwright',
                                job_id=self.job_id
                            )
                except Exception as e:
                    logger.warning(f"Error extracting video element: {e}")
                    continue

            await page.close()

        except Exception as e:
            logger.error(f"Playwright scraping error: {e}", exc_info=True)

            # Take screenshot on error if enabled
            if self.config_manager.get('robot2.screenshot_on_error', False, 'robot2'):
                try:
                    screenshot_path = f"error_screenshot_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved: {screenshot_path}")
                except:
                    pass

        return videos

    async def _extract_video_from_element(self, element, rank: int) -> Optional[Dict]:
        """
        Extract video data from a Playwright element.

        Args:
            element: Playwright element handle
            rank: Search result rank

        Returns:
            Dict with video data or None
        """
        try:
            # Extract video ID from link
            link = await element.query_selector('a#video-title')
            if not link:
                return None

            href = await link.get_attribute('href')
            if not href or '/watch?v=' not in href:
                return None

            video_id = href.split('v=')[1].split('&')[0]

            # Extract title
            title = await link.get_attribute('title')
            if not title:
                title_text = await link.inner_text()
                title = title_text.strip() if title_text else None

            # Extract channel name
            channel_name = None
            channel_link = await element.query_selector('ytd-channel-name a')
            if channel_link:
                channel_name = await channel_link.inner_text()
                channel_name = channel_name.strip() if channel_name else None

            # Extract view count (best effort)
            view_count = None
            metadata_line = await element.query_selector('#metadata-line')
            if metadata_line:
                text = await metadata_line.inner_text()
                # Parse view count from text like "1.2M views"
                if 'views' in text.lower():
                    view_text = text.split('views')[0].strip().split()[-1]
                    view_count = self._parse_view_count(view_text)

            # Extract thumbnail
            thumbnail = await element.query_selector('img')
            thumbnail_url = await thumbnail.get_attribute('src') if thumbnail else None

            return {
                'video_id': video_id,
                'title': title,
                'channel_name': channel_name,
                'view_count': view_count,
                'thumbnail_url': thumbnail_url,
                'search_rank': rank
            }

        except Exception as e:
            logger.warning(f"Error extracting video data from element: {e}")
            return None

    async def _scrape_with_api(self, query: str, max_results: int, search_query_id: int) -> List[Video]:
        """
        Scrape YouTube search results using YouTube Data API v3.

        Args:
            query: Search query
            max_results: Maximum number of videos to return
            search_query_id: ID of search query record

        Returns:
            List of Video objects
        """
        videos = []

        try:
            # Search for videos
            search_response = self.youtube_api_client.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                order='relevance'
            ).execute()

            # Extract video IDs
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            if not video_ids:
                return videos

            # Get detailed video statistics
            videos_response = self.youtube_api_client.videos().list(
                id=','.join(video_ids),
                part='snippet,statistics,contentDetails'
            ).execute()

            for index, item in enumerate(videos_response.get('items', [])):
                try:
                    video_data = self._parse_api_video(item, index + 1)
                    if video_data:
                        video = self._save_video(video_data, search_query_id)
                        if video:
                            videos.append(video)
                            # Broadcast video discovery event
                            await broadcast_video_discovered(
                                video_id=video.video_id,
                                title=video.title,
                                source='youtube_api',
                                job_id=self.job_id
                            )
                except Exception as e:
                    logger.warning(f"Error parsing API video: {e}")
                    continue

        except Exception as e:
            logger.error(f"YouTube API error: {e}", exc_info=True)

        return videos

    def _parse_api_video(self, item: Dict, rank: int) -> Optional[Dict]:
        """Parse video data from YouTube API response."""
        try:
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            content_details = item.get('contentDetails', {})

            # Parse duration (ISO 8601 format like PT1H2M30S)
            duration_seconds = None
            duration_str = content_details.get('duration', '')
            if duration_str:
                duration_seconds = self._parse_iso8601_duration(duration_str)

            # Parse published date
            published_at = None
            published_str = snippet.get('publishedAt')
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                except:
                    pass

            return {
                'video_id': item['id'],
                'channel_id': snippet.get('channelId'),
                'channel_name': snippet.get('channelTitle'),
                'title': snippet.get('title'),
                'description': snippet.get('description'),
                'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'duration_seconds': duration_seconds,
                'published_at': published_at,
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'search_rank': rank
            }

        except Exception as e:
            logger.warning(f"Error parsing API video data: {e}")
            return None

    def _save_video(self, video_data: Dict, search_query_id: int) -> Optional[Video]:
        """
        Save video to database (or update if exists).

        Args:
            video_data: Dict with video data
            search_query_id: ID of search query

        Returns:
            Video object or None
        """
        try:
            # Check if video already exists
            existing = self.db.query(Video).filter(
                Video.video_id == video_data['video_id']
            ).first()

            if existing:
                # Update existing video
                for key, value in video_data.items():
                    if key != 'search_rank' and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                self.db.commit()
                logger.debug(f"Updated existing video: {video_data['video_id']}")
                return existing
            else:
                # Create new video
                video = Video(
                    video_id=video_data['video_id'],
                    channel_id=video_data.get('channel_id'),
                    channel_name=video_data.get('channel_name'),
                    title=video_data['title'],
                    description=video_data.get('description'),
                    thumbnail_url=video_data.get('thumbnail_url'),
                    duration_seconds=video_data.get('duration_seconds'),
                    published_at=video_data.get('published_at'),
                    view_count=video_data.get('view_count'),
                    like_count=video_data.get('like_count'),
                    comment_count=video_data.get('comment_count'),
                    subscriber_count=video_data.get('subscriber_count'),
                    search_query_id=search_query_id,
                    search_rank=video_data.get('search_rank'),
                    metrics_analyzed=False,
                    format_classified=False,
                    transcript_downloaded=False
                )
                self.db.add(video)
                self.db.commit()
                self.db.refresh(video)
                logger.debug(f"Saved new video: {video_data['video_id']}")
                return video

        except Exception as e:
            logger.error(f"Error saving video {video_data.get('video_id')}: {e}")
            self.db.rollback()
            return None

    def _parse_view_count(self, view_text: str) -> Optional[int]:
        """Parse view count from text like '1.2M' or '500K'."""
        try:
            view_text = view_text.strip().upper()

            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}

            for suffix, multiplier in multipliers.items():
                if suffix in view_text:
                    number = float(view_text.replace(suffix, ''))
                    return int(number * multiplier)

            # No suffix, just parse as int
            return int(view_text.replace(',', ''))
        except:
            return None

    def _parse_iso8601_duration(self, duration: str) -> Optional[int]:
        """Parse ISO 8601 duration to seconds (e.g., PT1H2M30S -> 3750)."""
        try:
            import re

            pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
            match = re.match(pattern, duration)

            if not match:
                return None

            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)

            return hours * 3600 + minutes * 60 + seconds
        except:
            return None
