from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.webhook_security import verify_shared_secret
from app.models.entities import AffiliateLink, User
from app.providers.affiliate.shopee import MockAffiliateProvider
from app.services.affiliate_service import AffiliateService
from app.services.telegram_service import TelegramService
from app.schemas.common import AffiliateLinkRead

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramLinkRequest(BaseModel):
    token: str = Field(min_length=10)
    telegram_user_id: str = Field(min_length=1, max_length=255)


class TelegramGenerateLinkRequest(BaseModel):
    telegram_user_id: str = Field(min_length=1, max_length=255)
    original_url: str


@router.post("/link")
def create_link(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = TelegramService(db).create_link_token(current_user.id)
    db.commit()
    return {"token": token.token, "expires_at": token.expires_at, "command": f"/link {token.token}"}


def require_bot(x_bot_secret: str | None = Header(default=None, alias="X-Bot-Secret")) -> None:
    """
    Chỉ tiến trình bot mới được gọi các endpoint thay mặt người dùng.

    Không có lớp này thì chỉ cần biết `telegram_user_id` là tạo được link
    tracking gắn vào ví của người khác.
    """
    verify_shared_secret(x_bot_secret, get_settings().telegram_bot_secret, "Telegram bot")


@router.post("/link/confirm", dependencies=[Depends(require_bot)])
def confirm_link(payload: TelegramLinkRequest, db: Session = Depends(get_db)):
    try:
        account = TelegramService(db).link_account(payload.token, payload.telegram_user_id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "TELEGRAM_LINKED", "user_id": account.user_id}


@router.post("/generate-link", response_model=AffiliateLinkRead, dependencies=[Depends(require_bot)])
def generate_link(payload: TelegramGenerateLinkRequest, db: Session = Depends(get_db)) -> AffiliateLink:
    user_id = TelegramService(db).resolve_user_id(payload.telegram_user_id)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản Telegram chưa được liên kết")
    link = AffiliateService(db, MockAffiliateProvider()).generate_link(user_id, payload.original_url)
    db.commit()
    db.refresh(link)
    return link