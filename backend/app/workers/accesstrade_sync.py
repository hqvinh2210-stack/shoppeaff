from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.providers.affiliate.accesstrade import AccessTradeClient
from app.services.accesstrade_service import AccessTradeService
from app.services.cashback_reconciliation import CashbackReconciliationService


def sync_accesstrade(db: Session, since: datetime, until: datetime) -> dict[str, int]:
    settings = get_settings()
    if not settings.accesstrade_api_token:
        raise RuntimeError("ACCESSTRADE_API_TOKEN is not configured")
    client = AccessTradeClient(settings.accesstrade_api_token, settings.accesstrade_base_url, settings.accesstrade_timeout_seconds)
    service = AccessTradeService(db, client)
    cashback = CashbackReconciliationService(db, settings.cashback_rate_percent)
    inserted_or_updated_orders = 0
    inserted_or_updated_transactions = 0
    try:
        start = since.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        end = until.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for record in client.iter_orders(start, end, limit=300):
            service.upsert_order(record)
            inserted_or_updated_orders += 1
        for record in client.iter_transactions(start, end, limit=300):
            cashback.process_transaction(service.upsert_transaction(record))
            inserted_or_updated_transactions += 1
        db.commit()
    finally:
        client.close()
    return {"orders": inserted_or_updated_orders, "transactions": inserted_or_updated_transactions}