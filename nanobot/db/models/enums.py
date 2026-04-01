"""Shared enums for Mandala DB models."""

from enum import StrEnum


class ResearchType(StrEnum):
    MARKET_RESEARCH = "market_research"
    CUSTOMER_AVATAR = "customer_avatar"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    SALES_AVATAR_EXTENSION = "sales_avatar_extension"
    OFFER_BRIEF = "offer_brief"
    NECESSARY_BELIEFS = "necessary_beliefs"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkillName(StrEnum):
    MARKET_RESEARCH = "marketing-research"
    CUSTOMER_AVATAR = "customer-avatar"
    COMPETITOR_ANALYSIS = "competitor-analysis"
    MARKETING_FOUNDATION = "marketing-foundation"
    SALES_AVATAR_EXTENSION = "sales-avatar-extension"
    OFFER_BRIEF = "offer-brief"
    NECESSARY_BELIEFS = "necessary-beliefs"


RESEARCH_TYPE_TO_SKILL: dict[ResearchType, SkillName] = {
    ResearchType.MARKET_RESEARCH: SkillName.MARKET_RESEARCH,
    ResearchType.CUSTOMER_AVATAR: SkillName.CUSTOMER_AVATAR,
    ResearchType.COMPETITOR_ANALYSIS: SkillName.COMPETITOR_ANALYSIS,
}
