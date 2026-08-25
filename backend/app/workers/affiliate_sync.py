from sqlalchemy.orm import Session

from app.providers.affiliate.base import AffiliateProvider
from app.services.order_service import OrderService


def sync_affiliate_orders(db: Session, provider: AffiliateProvider) -> int:
    """
    Synchronize affiliate orders from a provider.

    Idempotency is enforced by the orders table unique constraint:
    (platform, platform_order_id). Orders without a valid tracking_id are
    moved to ATTRIBUTION_REVIEW by OrderService and are not credited.
    """
    imported_count = 0
    from app.core.config import get_settings

    order_service = OrderService(db, cashback_rate_percent=get_settings().cashback_rate_percent)

    for provider_order in provider.get_orders():
        order_service.upsert_order_from_affiliate(provider_order)
        imported_count += 1

    db.commit()
    return imported_count