"""
Tạo mới hoặc nâng quyền một tài khoản lên ADMIN.

Chạy từ thư mục `backend/`:

    # Nâng quyền tài khoản đã có (không cần biết mật khẩu)
    python -m scripts.create_admin --email ban@example.com --promote

    # Tạo tài khoản admin mới, script sẽ hỏi mật khẩu (không hiện trên màn hình)
    python -m scripts.create_admin --email admin@example.com --full-name "Quan tri"

    # Hạ quyền về USER
    python -m scripts.create_admin --email ban@example.com --demote

    # Xem ai đang là ADMIN
    python -m scripts.create_admin --list

Mật khẩu chỉ được nhập trực tiếp qua `getpass` và băm bằng argon2 trước khi
lưu; script không nhận mật khẩu qua tham số dòng lệnh để tránh lọt vào lịch sử
shell.
"""

import argparse
import sys
from getpass import getpass

from sqlalchemy import or_

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User
from app.models.enums import UserStatus
from app.services.wallet_service import WalletService

# Console Windows mặc định là cp1252, không in được tiếng Việt có dấu.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ADMIN_ROLE = "ADMIN"
USER_ROLE = "USER"
MIN_PASSWORD_LENGTH = 8


def find_user(db, identifier: str) -> User | None:
    return (
        db.query(User)
        .filter(or_(User.email == identifier, User.phone == identifier))
        .one_or_none()
    )


def read_new_password() -> str:
    password = getpass("Mật khẩu cho tài khoản admin: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Mật khẩu phải có tối thiểu {MIN_PASSWORD_LENGTH} ký tự.")
    if password != getpass("Nhập lại mật khẩu: "):
        sys.exit("Hai lần nhập không khớp.")
    return password


def main() -> None:
    parser = argparse.ArgumentParser(description="Quản lý tài khoản ADMIN")
    parser.add_argument("--email", help="Email hoặc số điện thoại của tài khoản")
    parser.add_argument("--full-name", default=None, help="Họ tên khi tạo mới")
    parser.add_argument("--promote", action="store_true", help="Nâng tài khoản đã có lên ADMIN")
    parser.add_argument("--demote", action="store_true", help="Hạ tài khoản về USER")
    parser.add_argument("--list", action="store_true", help="Liệt kê tài khoản ADMIN")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.list:
            admins = db.query(User).filter(User.role == ADMIN_ROLE).order_by(User.id).all()
            if not admins:
                print("Chưa có tài khoản ADMIN nào.")
            for admin in admins:
                print(f"#{admin.id} {admin.user_code} {admin.email or admin.phone} [{admin.status}]")
            return

        if not args.email:
            parser.error("Cần --email (hoặc dùng --list)")

        user = find_user(db, args.email)

        if args.demote:
            if user is None:
                sys.exit(f"Không tìm thấy tài khoản {args.email}")
            user.role = USER_ROLE
            db.commit()
            print(f"Đã hạ {args.email} về USER.")
            return

        if user is not None:
            if not args.promote and user.role != ADMIN_ROLE:
                sys.exit(
                    f"Tài khoản {args.email} đã tồn tại. Thêm --promote để nâng lên ADMIN "
                    "(mật khẩu hiện tại được giữ nguyên)."
                )
            user.role = ADMIN_ROLE
            user.status = UserStatus.ACTIVE.value
            WalletService(db).get_or_create_wallet(user.id)
            db.commit()
            print(f"Đã nâng {args.email} lên ADMIN (mật khẩu cũ giữ nguyên).")
            return

        if args.promote:
            sys.exit(f"Không tìm thấy tài khoản {args.email} để nâng quyền.")

        # Tạo mới: chấp nhận cả email lẫn số điện thoại làm định danh đăng nhập.
        is_phone = args.email.isdigit()
        user = User(
            user_code="PENDING",
            email=None if is_phone else args.email,
            phone=args.email if is_phone else None,
            password_hash=hash_password(read_new_password()),
            full_name=args.full_name,
            status=UserStatus.ACTIVE.value,
            role=ADMIN_ROLE,
        )
        db.add(user)
        db.flush()
        user.user_code = f"USR_{user.id}"
        WalletService(db).get_or_create_wallet(user.id)
        db.commit()
        print(f"Đã tạo tài khoản ADMIN {args.email} (mã {user.user_code}).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
