"""Article scheduling: generates pillar via nanobot first, then creates supporting ScheduledArticles."""

import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from nanobot.db.models.topic_cluster import (
    ScheduledArticle,
    TopicCluster,
    TopicKeyword,
    TopicPage,
)

DRIP_SCHEDULE_DAYS = [0, 1, 3, 4]  # Mon/Tue/Thu/Fri
DRIP_SCHEDULE_TIME = datetime.strptime("02:00", "%H:%M").time()
MAX_ARTICLES_PER_WEEK = 4


def _run_pillar_generation(
    pillar_scheduled_article_id: str,
    progress_callback: Callable[[str, int], None] | None = None,
) -> dict[str, Any] | None:
    """
    Generate the pillar article using nanobot (runs async from sync context).

    Uses a dedicated event loop and a fresh DB engine/session so that asyncpg
    connections are not shared with the main app loop.
    """
    result_holder: list[dict[str, Any] | None] = [None]

    async def _generate() -> None:
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from nanobot.config.mandala import MandalaConfig
        from nanobot.db.models.seo import SEOArticle
        from nanobot.services.seo.article_generator import generate_article

        cfg = MandalaConfig()
        engine = create_async_engine(
            cfg.async_database_url,
            echo=cfg.log_level == "DEBUG",
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        try:
            async with session_factory() as db:
                try:
                    r = await db.execute(
                        select(ScheduledArticle).where(
                            ScheduledArticle.id == UUID(pillar_scheduled_article_id),
                        )
                    )
                    pillar_sa = r.scalar_one_or_none()
                    if not pillar_sa:
                        return
                    if progress_callback:
                        try:
                            progress_callback("Starting pillar article generation...", 60)
                        except Exception:
                            pass
                    await generate_article(pillar_sa, db, progress_callback=progress_callback)
                    if pillar_sa.page_id:
                        page_r = await db.execute(select(TopicPage).where(TopicPage.id == pillar_sa.page_id))
                        page = page_r.scalar_one_or_none()
                        if page and page.seo_article_id:
                            seo_r = await db.execute(select(SEOArticle).where(SEOArticle.id == page.seo_article_id))
                            seo = seo_r.scalar_one_or_none()
                            if seo:
                                result_holder[0] = {
                                    "seo_article_id": str(seo.id),
                                    "shopify_article_url": seo.shopify_article_url,
                                    "status": seo.status or "draft_posted",
                                }
                    elif pillar_sa.topic_keyword_id:
                        tk_r = await db.execute(select(TopicKeyword).where(TopicKeyword.id == pillar_sa.topic_keyword_id))
                        tk = tk_r.scalar_one_or_none()
                        if tk and tk.seo_article_id:
                            seo_r = await db.execute(select(SEOArticle).where(SEOArticle.id == tk.seo_article_id))
                            seo = seo_r.scalar_one_or_none()
                            if seo:
                                result_holder[0] = {
                                    "seo_article_id": str(seo.id),
                                    "shopify_article_url": seo.shopify_article_url,
                                    "status": seo.status or "draft_posted",
                                }
                    await db.commit()
                except Exception:
                    await db.rollback()
                    raise
        finally:
            await engine.dispose()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_generate())
        return result_holder[0]
    finally:
        loop.close()


def _calculate_drip_schedule(article_count: int, start_date: Any) -> list[date]:
    schedule_dates: list[date] = []
    current_date = start_date.date() if isinstance(start_date, datetime) else start_date
    articles_scheduled = 0

    while articles_scheduled < article_count:
        days_ahead = 0
        while days_ahead < 7:
            check_date = current_date + timedelta(days=days_ahead)
            weekday = check_date.weekday()
            if weekday in DRIP_SCHEDULE_DAYS:
                schedule_dates.append(check_date)
                articles_scheduled += 1
                current_date = check_date + timedelta(days=1)
                break
            days_ahead += 1
        if schedule_dates and len(schedule_dates) % MAX_ARTICLES_PER_WEEK == 0:
            current_date = schedule_dates[-1] + timedelta(days=3)
    return schedule_dates[:article_count]


def _get_next_drip_date(start_date: Any, day_index: int) -> Any:
    target_weekday = DRIP_SCHEDULE_DAYS[day_index % len(DRIP_SCHEDULE_DAYS)]
    d = start_date.date() if isinstance(start_date, datetime) else start_date
    current_weekday = d.weekday()
    days_to_add = (target_weekday - current_weekday) % 7
    if days_to_add == 0 and current_weekday not in DRIP_SCHEDULE_DAYS:
        days_to_add = min(
            [(x - current_weekday) % 7 for x in DRIP_SCHEDULE_DAYS if (x - current_weekday) % 7 > 0],
            default=1,
        )
    return d + timedelta(days=days_to_add)


def _create_pillar_scheduled_article(
    db: Session,
    brand_id: UUID,
    topic_cluster_id: UUID,
    topic_keyword: TopicKeyword,
    pillar_page: TopicPage,
    pillar_keyword: str,
) -> ScheduledArticle:
    today = datetime.utcnow().date()
    pillar_scheduled_datetime = datetime.combine(today, DRIP_SCHEDULE_TIME)
    pillar_sa = ScheduledArticle(
        brand_id=brand_id,
        topic_cluster_id=topic_cluster_id,
        keyword=pillar_keyword,
        article_type="pillar",
        scheduled_datetime=pillar_scheduled_datetime,
        status="generating",
        priority="0",
        topic_keyword_id=topic_keyword.id,
        page_id=pillar_page.id,
    )
    db.add(pillar_sa)
    db.commit()
    db.refresh(pillar_sa)
    return pillar_sa


def _create_supporting_scheduled_articles(
    db: Session,
    brand_id: UUID,
    topic_cluster_id: UUID,
    topic_keyword: TopicKeyword,
    supporting_pages: list[TopicPage],
) -> list[ScheduledArticle]:
    schedule_dates = _calculate_drip_schedule(
        article_count=len(supporting_pages),
        start_date=datetime.utcnow().date(),
    )
    today = datetime.utcnow().date()
    scheduled_articles: list[ScheduledArticle] = []
    for idx, supporting_page in enumerate(supporting_pages):
        if idx < len(schedule_dates):
            scheduled_date = schedule_dates[idx]
        else:
            weeks_ahead = idx // MAX_ARTICLES_PER_WEEK
            day_index = idx % MAX_ARTICLES_PER_WEEK
            scheduled_date = _get_next_drip_date(today + timedelta(weeks=weeks_ahead), day_index)
        scheduled_datetime = datetime.combine(scheduled_date, DRIP_SCHEDULE_TIME)
        sa = ScheduledArticle(
            brand_id=brand_id,
            topic_cluster_id=topic_cluster_id,
            keyword=supporting_page.target_keyword,
            article_type="supporting",
            scheduled_datetime=scheduled_datetime,
            status="pending",
            priority=str(idx + 1),
            topic_keyword_id=topic_keyword.id,
            page_id=supporting_page.id,
        )
        db.add(sa)
        scheduled_articles.append(sa)
    db.commit()
    return scheduled_articles


def create_schedule(
    db: Session,
    brand_id: UUID,
    topic_cluster_id: UUID,
    pillar_keyword: str,
    progress_callback: Callable[[str, int], None] | None = None,
) -> dict[str, Any]:
    """
    Schedule topic cluster articles: generate pillar first (via nanobot), then schedule supporting.

    1. Generate pillar article (nanobot + seo-writer skill) -> post to Shopify, link to pillar page
    2. Create pillar ScheduledArticle (status=completed)
    3. Create supporting ScheduledArticles (status=pending)
    """
    if progress_callback:
        try:
            progress_callback("Loading topic cluster...", 5)
        except Exception:
            pass

    topic_cluster = (
        db.query(TopicCluster)
        .filter(
            TopicCluster.id == topic_cluster_id,
            TopicCluster.brand_id == brand_id,
        )
        .options(
            joinedload(TopicCluster.topic_keywords).joinedload(TopicKeyword.pages),
        )
        .first()
    )
    if not topic_cluster:
        raise ValueError("Topic cluster not found. Please verify the cluster ID is correct.")

    topic_keyword = next(
        (tk for tk in topic_cluster.topic_keywords if tk.keyword == pillar_keyword),
        None,
    )
    if not topic_keyword:
        raise ValueError(
            f"The pillar keyword '{pillar_keyword}' was not found in this topic cluster. "
            "Please verify the keyword matches one of the pillar topics in the cluster."
        )

    pillar_page = next((p for p in topic_keyword.pages if p.is_pillar), None)
    if not pillar_page:
        raise ValueError(f"Unable to find the pillar page for keyword '{pillar_keyword}'. The topic cluster may be incomplete.")

    existing = (
        db.query(ScheduledArticle)
        .filter(
            ScheduledArticle.topic_cluster_id == topic_cluster_id,
            ScheduledArticle.topic_keyword_id == topic_keyword.id,
        )
        .count()
    )
    if existing > 0:
        if progress_callback:
            try:
                progress_callback(f"Articles already scheduled for '{pillar_keyword}'...", 95)
            except Exception:
                pass
        scheduled_articles = (
            db.query(ScheduledArticle)
            .filter(
                ScheduledArticle.topic_cluster_id == topic_cluster_id,
                ScheduledArticle.topic_keyword_id == topic_keyword.id,
            )
            .all()
        )
        return {
            "scheduled_count": len(scheduled_articles),
            "schedule_dates": sorted(list({sa.scheduled_datetime.date() for sa in scheduled_articles})),
            "pillar_article": None,
        }

    supporting_pages = [p for p in topic_keyword.pages if not p.is_pillar]
    if progress_callback:
        try:
            progress_callback("Generating pillar article...", 20)
        except Exception:
            pass

    pillar_sa = _create_pillar_scheduled_article(
        db=db,
        brand_id=brand_id,
        topic_cluster_id=topic_cluster_id,
        topic_keyword=topic_keyword,
        pillar_page=pillar_page,
        pillar_keyword=pillar_keyword,
    )
    pillar_info: dict[str, Any] | None = None
    try:
        pillar_info = _run_pillar_generation(str(pillar_sa.id), progress_callback)
        pillar_sa.status = "completed"
    except Exception as e:
        logger.warning("Pillar generation failed: {}", str(e))
        pillar_sa.status = "failed"
    db.commit()

    if progress_callback:
        try:
            progress_callback("Scheduling supporting articles...", 90)
        except Exception:
            pass

    supporting_articles = _create_supporting_scheduled_articles(
        db=db,
        brand_id=brand_id,
        topic_cluster_id=topic_cluster_id,
        topic_keyword=topic_keyword,
        supporting_pages=supporting_pages,
    )
    scheduled_articles = [pillar_sa] + supporting_articles
    schedule_dates = sorted(list({sa.scheduled_datetime.date() for sa in scheduled_articles}))

    return {
        "scheduled_count": len(scheduled_articles),
        "schedule_dates": schedule_dates,
        "pillar_article": pillar_info,
    }


class ArticleScheduler:
    """Generates pillar via nanobot, then creates supporting ScheduledArticles."""

    def schedule_topic_cluster_articles(
        self,
        brand_id: UUID,
        topic_cluster_id: UUID,
        db: Any,
        pillar_keyword: str | None = None,
        progress_callback: Callable[[str, int], None] | None = None,
        shopify_access_token: str | None = None,
        blog_id: str | None = None,
        shop_domain: str | None = None,
    ) -> dict[str, Any]:
        return create_schedule(
            db=db,
            brand_id=brand_id,
            topic_cluster_id=topic_cluster_id,
            pillar_keyword=pillar_keyword or "",
            progress_callback=progress_callback,
        )
