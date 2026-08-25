from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.entities import User
from app.models.enums import UserStatus
from app.schemas.common import (
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)
from app.services.email_service import EmailService
from app.services.wallet_service import WalletService
from app.utils.phone import normalize_phone

router = APIRouter(tags=["auth"])


def _queue_welcome_email(background_tasks: BackgroundTasks, user: User) -> None:
    """
    Xếp thư chào mừng vào hàng chạy nền.

    Chạy nền vì SMTP có thể mất vài giây; người dùng không phải chờ, và máy chủ
    mail hỏng cũng không làm hỏng việc tạo tài khoản (EmailService nuốt lỗi).
    Tài khoản đăng ký bằng số điện thoại thì không có gì để gửi.
    """
    if not user.email:
        return
    background_tasks.add_task(
        EmailService().send_welcome, user.email, user.full_name, user.user_code
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenPair:
    normalized_phone = normalize_phone(payload.phone)
    if not payload.email and not payload.phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cần nhập email hoặc số điện thoại")

    existing = (
        db.query(User)
        .filter(or_(User.email == payload.email if payload.email else False, User.phone == normalized_phone if normalized_phone else False))
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email hoặc số điện thoại đã được đăng ký")

    user = User(
        user_code="PENDING",
        email=payload.email,
        phone=normalized_phone,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    user.user_code = f"USR_{user.id}"
    WalletService(db).get_or_create_wallet(user.id)
    db.commit()
    _queue_welcome_email(background_tasks, user)

    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    normalized_phone = normalize_phone(payload.identifier)
    user = db.query(User).filter(or_(User.email == payload.identifier, User.phone == normalized_phone)).one_or_none()
    if user is None and normalized_phone:
        # Tương thích với tài khoản cũ được lưu trước khi chuẩn hóa số điện thoại.
        user = next(
            (candidate for candidate in db.query(User).filter(User.phone.is_not(None)).all()
             if normalize_phone(candidate.phone) == normalized_phone),
            None,
        )
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email/số điện thoại hoặc mật khẩu không đúng")
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đang bị khoá")

    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/google", response_model=TokenPair)
def google_login(
    payload: GoogleLoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> TokenPair:
    client_id = get_settings().google_client_id
    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Đăng nhập Google chưa được cấu hình")
    try:
        response = httpx.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": payload.id_token}, timeout=5)
        response.raise_for_status()
        claims = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Google không hợp lệ") from exc

    if claims.get("aud") != client_id or claims.get("email_verified") not in (True, "true") or not claims.get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản Google chưa được xác minh")

    email = claims["email"].lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(user_code="PENDING", email=email, full_name=claims.get("name"), status=UserStatus.ACTIVE.value)
        db.add(user)
        db.flush()
        user.user_code = f"USR_{user.id}"
        WalletService(db).get_or_create_wallet(user.id)
        db.commit()
        # Chỉ chào mừng tài khoản vừa được tạo, không gửi lại mỗi lần đăng nhập.
        _queue_welcome_email(background_tasks, user)
    elif user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đang bị khoá")

    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """
    Đổi refresh token lấy cặp token mới.

    Trước đây backend cấp refresh token nhưng không có chỗ dùng, nên phiên chết
    hẳn sau 30 phút và người dùng bị đá ra giữa thao tác.
    """
    try:
        claims = decode_refresh_token(payload.refresh_token)
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token không hợp lệ"
        ) from None

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại")
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đang bị khoá")

    subject = str(user.id)
    return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


@router.post("/logout")
def logout() -> dict[str, str]:
    # Không có danh sách thu hồi: access token vẫn hợp lệ tới khi hết hạn.
    # Frontend chịu trách nhiệm xoá cả access lẫn refresh token khỏi máy.
    return {"status": "OK"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user