"""
Gửi thử thư chào mừng để kiểm tra cấu hình SMTP.

Chạy từ thư mục `backend/`:

    python -m scripts.send_test_email --to ban@example.com

Script in ra cấu hình đang dùng (che mật khẩu) rồi gửi đúng nội dung mà người
dùng mới nhận được, nên có thể dùng để soát lại bố cục email trước khi phát hành.
"""

import argparse
import sys

from app.core.config import get_settings
from app.services.email_service import EmailService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gửi thử email chào mừng")
    parser.add_argument("--to", required=True, help="Địa chỉ nhận thư thử")
    parser.add_argument("--name", default="Nguyễn Văn A", help="Họ tên hiển thị trong thư")
    parser.add_argument("--user-code", default="USR_TEST", help="Mã tài khoản hiển thị")
    args = parser.parse_args()

    settings = get_settings()
    print(f"SMTP host     : {settings.smtp_host}:{settings.smtp_port}")
    print(f"SMTP username : {settings.smtp_username}")
    print(f"SMTP password : {'(đã đặt)' if settings.smtp_password else '(trống)'}")
    print(f"Gửi từ        : {settings.sender_address}")
    print(f"Đã bật email  : {settings.email_enabled}")

    if not settings.email_enabled:
        sys.exit("Chưa cấu hình đủ SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD trong .env")

    print(f"\nĐang gửi tới {args.to} ...")
    ok = EmailService().send_welcome(args.to, args.name, args.user_code)
    if ok:
        print("Đã gửi thành công. Kiểm tra hộp thư (kể cả mục Spam).")
    else:
        sys.exit("Gửi thất bại — xem log phía trên để biết lý do.")


if __name__ == "__main__":
    main()
