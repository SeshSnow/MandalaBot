"""
Article Generator - Generates SEO articles via nanobot (seo-writer skill).

Uses a two-phase agent flow (title+abstract → outline+article) via the shared
AgentLoop. Used for both scheduled article generation (cron) and manual generation.
"""

SEO_WRITER_SKILL = "seo-writer"
SEO_WRITER_REF_OUTLINE_RULES = "references/outline-rules.md"

from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

import markdown
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.brand import Brand
from nanobot.db.models.seo import SEOArticle
from nanobot.db.models.topic_cluster import LongTailKeyword, ScheduledArticle, TopicKeyword, TopicPage
from nanobot.services.shopify.graphql.blog_queries import GET_BLOGS
from nanobot.services.shopify.shopify_client import ShopifyClient
from nanobot.services.shopify.shopify_credentials_service import ShopifyCredentialsService


async def _get_pillar_article_context(scheduled_article: ScheduledArticle, db: AsyncSession) -> tuple[str | None, str | None]:
    if scheduled_article.article_type != "supporting" or not scheduled_article.topic_keyword_id:
        return (None, None)
    result = await db.execute(
        select(TopicPage).where(TopicPage.topic_keyword_id == scheduled_article.topic_keyword_id, TopicPage.is_pillar.is_(True))
    )
    pillar_page = result.scalar_one_or_none()
    if not pillar_page or not pillar_page.seo_article_id:
        return (None, None)
    art_result = await db.execute(select(SEOArticle).where(SEOArticle.id == pillar_page.seo_article_id))
    pillar_article = art_result.scalar_one_or_none()
    if not pillar_article or not pillar_article.shopify_article_url:
        return (None, None)
    return (pillar_article.shopify_article_url, pillar_article.title or None)


async def _get_longtail_keywords(scheduled_article: ScheduledArticle, db: AsyncSession) -> list[str]:
    if not scheduled_article.page_id:
        return []
    result = await db.execute(
        select(LongTailKeyword.keyword).where(LongTailKeyword.page_id == scheduled_article.page_id).order_by(LongTailKeyword.order_index)
    )
    return [row[0] for row in result.all()]


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        first = lines[0].strip()
        if first == "```" or first.startswith("```"):
            lines = lines[1:]
        s = "\n".join(lines)
    if s.endswith("```"):
        s = s[: s.rfind("```")].rstrip()
    return s.strip()


def _parse_title_abstract(response: str) -> tuple[str, str]:
    s = response.strip()
    if not s:
        raise ValueError("Title+abstract response was empty")
    if "\n\n" in s:
        title_part, abstract_part = s.split("\n\n", 1)
        title = title_part.strip()
        abstract = abstract_part.strip()
    else:
        lines = s.split("\n")
        title = lines[0].strip() if lines else ""
        abstract = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    if not title:
        raise ValueError("Could not parse title from phase 1 response")
    if not abstract:
        raise ValueError("Could not parse abstract from phase 1 response")
    return title, abstract


def _build_phase1_prompt(keyword, brand_name, description, target_audience, brand_voice, shop_domain, article_type, pillar_article_url=None, pillar_title=None, longtail_keywords=None) -> str:
    lines = [
        f"Use the {SEO_WRITER_SKILL} skill for **Phase 1 only** (title and abstract). "
        "Follow the skill's Phase 1 instructions; output only the title on the first line, "
        "then a blank line, then the abstract.",
        "",
        "Context:",
        f"- Focus keyword: {keyword}",
        f"- Brand: {brand_name}. Description: {description}",
    ]
    if target_audience:
        lines.append(f"- Target audience: {target_audience}")
    if brand_voice:
        lines.append(f"- Brand voice: {brand_voice}")
    if shop_domain:
        lines.append(f"- Shop domain: {shop_domain}")
    if article_type == "supporting" and pillar_article_url and pillar_title:
        lines.append(f"- Supporting article: link to pillar \"{pillar_title}\" at {pillar_article_url}")
    if longtail_keywords:
        lines.append(f"- Supporting keywords to weave in: {', '.join(longtail_keywords)}")
    return "\n".join(lines)


def _build_phase2_prompt(title, abstract, keyword, brand_name, description, brand_voice, shop_domain, article_type, pillar_article_url=None, pillar_title=None, longtail_keywords=None) -> str:
    lines = [
        f"Use the {SEO_WRITER_SKILL} skill for **Phase 2** (outline + article). "
        f"Follow the skill reference **{SEO_WRITER_REF_OUTLINE_RULES}** for outline format. "
        "Output the outline (markdown starting with #), then a blank line, then the full article body.",
        "",
        "Context:",
        f"- Title: \"{title}\"",
        f"- Abstract: \"{abstract}\"",
        f"- Focus keyword: {keyword}",
        f"- Brand: {brand_name}. {description}",
    ]
    if longtail_keywords:
        lines.append(f"- Supporting keywords to weave in: {', '.join(longtail_keywords)}")
    if brand_voice:
        lines.append(f"- Brand voice: {brand_voice}")
    if shop_domain:
        lines.append(f"- Shop domain: {shop_domain}")
    if article_type == "supporting" and pillar_article_url and pillar_title:
        lines.append(f"- Link to pillar \"{pillar_title}\" at {pillar_article_url} in a natural section")
    return "\n".join(lines)


def _parse_phase2_response(response: str) -> str:
    s = response.strip()
    if not s:
        raise ValueError("Phase 2 response was empty")
    parts = s.split("\n\n")
    if len(parts) < 2:
        parts = s.split("\n", 1)
    if len(parts) < 2:
        raise ValueError("Could not parse outline and article from Phase 2 response")
    outline_block = parts[0].strip()
    article_body_md = "\n\n".join(parts[1:]).strip()
    if not outline_block or not outline_block.startswith("#"):
        raise ValueError("Could not parse outline from Phase 2 response")
    if not article_body_md:
        raise ValueError("Could not parse article body from Phase 2 response")
    return article_body_md


async def _process_message(prompt: str, session_key: str) -> str:
    """Run a message through the shared agent loop."""
    from nanobot.api.agent_context import get_agent_loop
    from nanobot.api.integration import process_message
    agent_loop = get_agent_loop()
    return await process_message(agent_loop, prompt, session_key)


async def create_article(shop_domain: str, title: str, summary: str, body_html: str, db: AsyncSession, blog_id: str | None = None, draft: bool = True) -> dict[str, Any]:
    """Post an SEO article to Shopify as a draft or published blog article."""
    credentials_service = ShopifyCredentialsService()
    access_token = await credentials_service.get_token(shop_domain, db)
    store_config = {"domain": shop_domain, "accessToken": access_token, "apiVersion": "2025-04"}
    shopify_client = ShopifyClient(store_config)

    blog_id_to_use = blog_id
    if not blog_id_to_use:
        blogs_result = shopify_client.execute_query(GET_BLOGS)
        blogs = blogs_result.get("blogs", {}).get("edges", [])
        if not blogs:
            raise ValueError("No blogs found in Shopify store")
        blog_id_to_use = blogs[0]["node"]["id"]

    return shopify_client.blog.create_article_draft(blog_id=blog_id_to_use, title=title, body_html=body_html, summary=summary, draft=draft)


async def generate_article(scheduled_article: ScheduledArticle, db: AsyncSession, progress_callback: Callable[[str, int], None] | None = None) -> None:
    """Generate a single article via nanobot, post to Shopify."""
    result = await db.execute(select(Brand).where(Brand.id == scheduled_article.brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise ValueError(f"Brand not found for ID: {scheduled_article.brand_id}")

    shopify_store_id = brand.shopify_store_id
    target_audience = None
    brand_voice = None
    if brand.context_config_json:
        context = brand.context_config_json
        target_audience = context.get("target_audience")
        brand_voice = context.get("brand_voice")

    pillar_article_url = pillar_title = None
    if scheduled_article.article_type == "supporting":
        pillar_article_url, pillar_title = await _get_pillar_article_context(scheduled_article, db)

    longtail_keywords: list[str] = await _get_longtail_keywords(scheduled_article, db)
    session_key = f"article:{scheduled_article.id}:{uuid4().hex[:8]}"
    brand_desc = brand.description or ""

    def _progress(msg: str, pct: int) -> None:
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except Exception:
                pass

    _progress("Generating title and abstract...", 62)
    prompt1 = _build_phase1_prompt(
        keyword=scheduled_article.keyword, brand_name=brand.brand_name, description=brand_desc,
        target_audience=target_audience, brand_voice=brand_voice, shop_domain=shopify_store_id,
        article_type=scheduled_article.article_type, pillar_article_url=pillar_article_url,
        pillar_title=pillar_title, longtail_keywords=longtail_keywords or None,
    )
    response1 = await _process_message(prompt1, session_key)
    title, abstract = _parse_title_abstract(response1)

    _progress("Generating outline and article...", 72)
    prompt2 = _build_phase2_prompt(
        title=title, abstract=abstract, keyword=scheduled_article.keyword, brand_name=brand.brand_name,
        description=brand_desc, brand_voice=brand_voice, shop_domain=shopify_store_id,
        article_type=scheduled_article.article_type, pillar_article_url=pillar_article_url,
        pillar_title=pillar_title, longtail_keywords=longtail_keywords or None,
    )
    response2 = await _process_message(prompt2, session_key)
    article_body_md = _parse_phase2_response(_strip_code_fence(response2.strip()))
    body_html = markdown.markdown(article_body_md)

    seo_article = SEOArticle(brand_id=brand.id, title=title, abstract=abstract, status="outline_generated")
    db.add(seo_article)
    await db.commit()
    await db.refresh(seo_article)

    _progress("Posting to Shopify...", 92)
    article_result = await create_article(shop_domain=shopify_store_id, title=seo_article.title, summary=seo_article.abstract or "", body_html=body_html, db=db)

    seo_article.shopify_article_id = article_result.get("id")
    shopify_url = article_result.get("adminUrl")
    if not shopify_url and article_result.get("id") and shopify_store_id:
        article_id = str(article_result.get("id", "")).replace("gid://shopify/Article/", "")
        store_handle = shopify_store_id.split(".")[0] if "." in shopify_store_id else shopify_store_id
        if article_id and store_handle:
            shopify_url = f"https://admin.shopify.com/store/{store_handle}/content/articles/{article_id}"
    seo_article.shopify_article_url = shopify_url
    seo_article.status = "draft_posted"
    await db.commit()
    await db.refresh(seo_article)

    if scheduled_article.page_id:
        page_r = await db.execute(select(TopicPage).where(TopicPage.id == scheduled_article.page_id))
        page = page_r.scalar_one_or_none()
        if page:
            page.seo_article_id = seo_article.id
            page.article_created_at = datetime.utcnow()
            if page.is_pillar and scheduled_article.topic_keyword_id:
                tk_r = await db.execute(select(TopicKeyword).where(TopicKeyword.id == scheduled_article.topic_keyword_id))
                tk = tk_r.scalar_one_or_none()
                if tk and not tk.seo_article_id:
                    tk.seo_article_id = seo_article.id
                    tk.article_created_at = datetime.utcnow()
    elif scheduled_article.topic_keyword_id:
        tk_r = await db.execute(select(TopicKeyword).where(TopicKeyword.id == scheduled_article.topic_keyword_id))
        topic_keyword = tk_r.scalar_one_or_none()
        if topic_keyword and not topic_keyword.seo_article_id:
            topic_keyword.seo_article_id = seo_article.id
            topic_keyword.article_created_at = datetime.utcnow()

    await db.commit()
    logger.success(f"Successfully generated article for keyword: {scheduled_article.keyword}")
