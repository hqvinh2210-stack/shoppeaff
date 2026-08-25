"""
Kéo đơn hàng và giao dịch từ AccessTrade về database.

Worker `app.workers.accesstrade_sync` đã có sẵn nhưng không có gì gọi nó — không
scheduler, không endpoint, không CLI. Script này là chỗ gọi đó.

Chạy từ thư mục `backend/`:

    # Xem AccessTrade trả về gì mà không ghi vào DB — chạy cái này trước tiên
    python -m scripts.sync_accesstrade --days 7 --dry-run

    # Kéo thật 7 ngày gần nhất
    python -m scripts.sync_accesstrade --days 7

    # Kéo một khoảng cụ thể
    python -m scripts.sync_accesstrade --since 2026-08-01T00:00:00Z --until 2026-08-25T00:00:00Z

Cần `ACCESSTRADE_API_TOKEN` trong `backend/.env`. API giới hạn 10 request/phút
nên đừng chạy liên tục; một lần mỗi 15–30 phút là đủ dày cho hoàn tiền.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.providers.affiliate.accesstrade import AccessTradeClient
from app.workers.accesstrade_sync import sync_accesstrade

# Console Windows mặc định là cp1252, không in được tiếng Việt có dấu. Phải set
# cả stderr vì `sys.exit("...")` in thông báo lỗi ra đó, không phải stdout.
for _luong in (sys.stdout, sys.stderr):
    if hasattr(_luong, "reconfigure"):
        _luong.reconfigure(encoding="utf-8", errors="replace")


def parse_moment(value: str) -> datetime:
    """Nhận ISO8601, chấp nhận cả hậu tố 'Z' mà `fromisoformat` cũ không hiểu."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def resolve_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    until = parse_moment(args.until) if args.until else datetime.now(timezone.utc)
    since = parse_moment(args.since) if args.since else until - timedelta(days=args.days)
    if since >= until:
        sys.exit("Mốc --since phải nhỏ hơn --until.")
    return since, until


def run_dry(since: datetime, until: datetime, limit: int) -> None:
    """
    Gọi API và in nguyên văn bản ghi đầu tiên, không đụng vào DB.

    Bước này đáng làm trước khi kéo thật: nó cho thấy AccessTrade thực sự trả về
    tên trường gì, đủ để đối chiếu với `AccessTradeService.upsert_*` trước khi có
    bản ghi nào được ghi xuống.
    """
    settings = get_settings()
    client = AccessTradeClient(
        settings.accesstrade_api_token,
        settings.accesstrade_base_url,
        settings.accesstrade_timeout_seconds,
    )
    start = since.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    end = until.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        for nhan, lay in (("ĐƠN HÀNG", client.iter_orders), ("GIAO DỊCH", client.iter_transactions)):
            print(f"\n===== {nhan} =====")
            dem = 0
            for record in lay(start, end, limit=limit):
                if dem == 0:
                    print("Bản ghi đầu tiên, nguyên văn:")
                    print(json.dumps(record, ensure_ascii=False, indent=2, default=str)[:2000])
                    print("\nCác khoá:", sorted(record.keys()))
                dem += 1
            print(f"Tổng: {dem} bản ghi (không ghi vào DB).")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Đồng bộ đơn và giao dịch từ AccessTrade")
    parser.add_argument("--days", type=int, default=7, help="Số ngày lùi về trước nếu không nêu --since (mặc định 7)")
    parser.add_argument("--since", default=None, help="Mốc đầu, ISO8601 vd 2026-08-01T00:00:00Z")
    parser.add_argument("--until", default=None, help="Mốc cuối, ISO8601; mặc định là bây giờ")
    parser.add_argument("--limit", type=int, default=100, help="Số bản ghi mỗi trang (mặc định 100)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ gọi API và in ra, không ghi DB")
    args = parser.parse_args()

    if not get_settings().accesstrade_api_token:
        sys.exit(
            "Thiếu ACCESSTRADE_API_TOKEN trong backend/.env.\n"
            "Thêm dòng sau rồi chạy lại:\n"
            "    ACCESSTRADE_API_TOKEN=<token lấy từ dashboard AccessTrade>"
        )

    since, until = resolve_window(args)
    print(f"Khoảng đồng bộ: {since.isoformat()} → {until.isoformat()}")

    if args.dry_run:
        run_dry(since, until, args.limit)
        return

    db = SessionLocal()
    try:
        ket_qua = sync_accesstrade(db, since, until, limit=args.limit)
        print(f"Đã ghi/cập nhật: {ket_qua['orders']} đơn, {ket_qua['transactions']} giao dịch.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
