"""
Scheduled Article Generator - Cron task for generating scheduled articles.
"""

import traceback
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.topic_cluster import ScheduledArticle
from nanobot.services.seo.article_generator import generate_article


class ScheduledArticleGenerator:
    """Cron task that generates scheduled articles automatically."""

    async def process_scheduled_articles(self, db: AsyncSession) -> dict[str, Any]:
        scheduled_articles = await self._get_next_scheduled_articles(limit=20, db=db)

        if not scheduled_articles:
            logger.info("No scheduled articles ready to generate")
            return {"processed": 0, "completed": 0, "failed": 0, "errors": []}

        logger.info(f"Processing {len(scheduled_articles)} scheduled articles")
        results: dict[str, Any] = {"processed": 0, "completed": 0, "failed": 0, "errors": []}

        for scheduled_article in scheduled_articles:
            try:
                scheduled_article.status = "generating"
                await db.commit()
                await generate_article(scheduled_article, db)
                scheduled_article.status = "completed"
                await db.commit()
                results["completed"] += 1
                results["processed"] += 1
                logger.success(f"Successfully generated article for keyword: {scheduled_article.keyword}")
            except Exception as e:
                error_msg = f"Failed to generate article for {scheduled_article.keyword}: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                scheduled_article.status = "failed"
                await db.commit()
                results["failed"] += 1
                results["processed"] += 1
                results["errors"].append({"keyword": scheduled_article.keyword, "error": error_msg})

        return results

    async def _get_next_scheduled_articles(self, limit: int, db: AsyncSession) -> list[ScheduledArticle]:
        today = datetime.utcnow()
        result = await db.execute(
            select(ScheduledArticle)
            .where(ScheduledArticle.status == "pending", ScheduledArticle.scheduled_datetime <= today)
            .order_by(ScheduledArticle.priority.asc(), ScheduledArticle.scheduled_datetime.asc())
            .limit(limit)
        )
        scheduled_articles = result.scalars().all()

        filtered_articles: list[ScheduledArticle] = []
        cluster_weekly_counts: dict[str, int] = {}
        max_articles_per_week = 4

        for article in scheduled_articles:
            cluster_id = str(article.topic_cluster_id)
            week_start = today.date() - timedelta(days=today.date().weekday())
            week_start_datetime = datetime.combine(week_start, datetime.min.time())

            if cluster_id not in cluster_weekly_counts:
                count_result = await db.execute(
                    select(ScheduledArticle).where(
                        ScheduledArticle.topic_cluster_id == article.topic_cluster_id,
                        ScheduledArticle.status == "completed",
                        ScheduledArticle.scheduled_datetime >= week_start_datetime,
                    )
                )
                cluster_weekly_counts[cluster_id] = len(count_result.scalars().all())

            if cluster_weekly_counts[cluster_id] < max_articles_per_week:
                filtered_articles.append(article)
                cluster_weekly_counts[cluster_id] += 1

        return filtered_articles


async def run_scheduled_article_generator(db: AsyncSession) -> dict[str, Any]:
    generator = ScheduledArticleGenerator()
    results = await generator.process_scheduled_articles(db)
    logger.info(f"Scheduled article generation completed: {results}")
    return results
