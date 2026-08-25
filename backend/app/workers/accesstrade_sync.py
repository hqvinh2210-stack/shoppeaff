from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.providers.affiliate.accesstrade import AccessTradeClient
from app.services.accesstrade_service import AccessTradeService
from app.services.cashback_reconciliation import CashbackReconciliationService


def sync_accesstrade(db: Session, since: datetime, until: datetime, limit: int = 100) -> dict[str, int]:
    """
    `limit` phải bằng đúng số bản ghi mỗi trang mà AccessTrade thực sự trả về.

    `iter_orders`/`iter_transactions` dừng phân trang khi một trang trả về ít hơn
    `limit`. Khai `limit` lớn hơn mức trần thật của API sẽ khiến trang đầu tiên
    luôn trông như trang cuối, và phần dữ liệu còn lại bị bỏ im lặng — không lỗi,
    không cảnh báo, chỉ thiếu đơn.

    Theo tài liệu chính thức, hai endpoint không giống nhau:
      - /v1/orders       mặc định 30, tối đa 300 (điền quá 300 thì bị ép về 300)
      - /v1/transactions mặc định 100

    Giá trị 300 dùng trước đây nguy hiểm ở cả hai phía: với /orders nó nằm sát
    ngưỡng bị ép, với /transactions nó vượt xa mặc định. Chọn 100 vì an toàn cho
    cả hai. Cũng đừng gọi dồn: API giới hạn 10 request/phút.
    """
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
        for record in client.iter_orders(start, end, limit=limit):
            service.upsert_order(record)
            inserted_or_updated_orders += 1
        for record in client.iter_transactions(start, end, limit=limit):
            cashback.process_transaction(service.upsert_transaction(record))
            inserted_or_updated_transactions += 1
        db.commit()
    finally:
        client.close()
    return {"orders": inserted_or_updated_orders, "transactions": inserted_or_updated_transactions}