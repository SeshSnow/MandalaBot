"""
Token service for managing shop token balances and billing cycles.
Implements lazy refill logic that checks and resets tokens on-demand.
"""

from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.shop import ShopSubscription

# Domains that receive free Elite membership (manual override)
ELITE_FREE_DOMAINS = [
    "0e501b.myshopify.com",
    "mandala-dev-store-3.myshopify.com",
]


def _get_config():
    from nanobot.config.mandala import MandalaConfig
    return MandalaConfig()


class TokenService:
    """
    Service for managing token balances and billing cycles.

    Implements lazy refill logic:
    - Basic plan: No reset (one-time tokens)
    - Paid plans: Reset to plan limit after 30 days
    """

    def is_elite_free_domain(self, shop_domain: str) -> bool:
        normalized = shop_domain.lower().strip()
        return normalized in [d.lower().strip() for d in ELITE_FREE_DOMAINS]

    def get_plan_token_limit(self, plan_name: str, billing_interval: str | None = None) -> int:
        cfg = _get_config()
        limits = {
            "basic": cfg.token_limit_free,
            "premium": cfg.token_limit_premium,
            "elite": cfg.token_limit_elite,
        }
        base_limit = limits.get(plan_name.lower(), cfg.token_limit_free)

        if billing_interval == "ANNUAL":
            if plan_name.lower() == "premium":
                return cfg.token_limit_premium * 12
            elif plan_name.lower() == "elite":
                return cfg.token_limit_elite * 12

        return base_limit

    async def check_and_refill_tokens(self, shop_domain: str, db: AsyncSession) -> bool:
        cfg = _get_config()
        try:
            result = await db.execute(select(ShopSubscription).where(ShopSubscription.shopify_store_id == shop_domain))
            shop = result.scalars().first()

            if not shop:
                logger.warning(f"Shop not found: {shop_domain}")
                return False

            if self.is_elite_free_domain(shop_domain) and shop.plan_name != "elite":
                shop.plan_name = "elite"
                shop.subscription_id = None
                shop.billing_interval = "EVERY_30_DAYS"
                shop.billing_cycle_start = datetime.utcnow()
                shop.tokens_remaining = cfg.token_limit_elite
                await db.commit()
                logger.info(f"Applied free elite override for {shop_domain}")
                return True

            if shop.plan_name == "basic":
                return True

            if shop.billing_cycle_start is None:
                shop.billing_cycle_start = datetime.utcnow()
                await db.commit()
                return True

            now = datetime.utcnow()
            days_since_start = (now - shop.billing_cycle_start).days
            refill_period = 365 if shop.billing_interval == "ANNUAL" else 30

            if days_since_start >= refill_period:
                plan_limit = self.get_plan_token_limit(shop.plan_name, shop.billing_interval)
                shop.tokens_remaining = plan_limit
                shop.billing_cycle_start = now
                await db.commit()
                logger.info(f"Refilled tokens for {shop_domain}: {plan_limit}")
                return True

            return True

        except Exception as e:
            logger.error(f"Error checking/refilling tokens for {shop_domain}: {str(e)}")
            return False

    async def initialize_shop(self, shop_domain: str, db: AsyncSession) -> ShopSubscription | None:
        cfg = _get_config()
        try:
            result = await db.execute(select(ShopSubscription).where(ShopSubscription.shopify_store_id == shop_domain))
            existing_shop = result.scalars().first()

            if existing_shop:
                if existing_shop.is_deleted:
                    existing_shop.is_deleted = False
                    existing_shop.updated_at = datetime.utcnow()
                    await db.commit()
                return existing_shop

            new_shop = ShopSubscription(
                shopify_store_id=shop_domain,
                plan_name="basic",
                subscription_id=None,
                tokens_remaining=cfg.token_limit_free,
                billing_cycle_start=None,
                is_deleted=False,
            )
            db.add(new_shop)
            await db.commit()
            await db.refresh(new_shop)
            logger.info(f"Initialized new shop: {shop_domain}")
            return new_shop

        except Exception as e:
            logger.error(f"Error initializing shop {shop_domain}: {str(e)}")
            await db.rollback()
            return None

    async def get_shop(self, shop_domain: str, db: AsyncSession, include_deleted: bool = False) -> ShopSubscription | None:
        stmt = select(ShopSubscription).where(ShopSubscription.shopify_store_id == shop_domain)
        if not include_deleted:
            stmt = stmt.where(ShopSubscription.is_deleted.is_(False))
        result = await db.execute(stmt)
        return result.scalars().first()
