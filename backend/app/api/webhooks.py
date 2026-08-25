from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.webhook_security import verify_signature
from app.models.entities import AffiliateLink
from app.providers.affiliate.shopee import MockAffiliateProvider
from app.schemas.common import ZaloWebhookRequest
from app.services.affiliate_service import AffiliateService
from app.services.zalo_service import ZaloService
from app.utils.url_parser import find_shopee_url

router = APIRouter(tags=["webhooks"])


@router.post("/zalo")
async def zalo_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_zalo_signature: str | None = Header(default=None),
) -> dict[str, str | int | None]:
    # Trước đây chỉ kiểm header có tồn tại hay không — ai cũng giả mạo được tin
    # nhắn và tạo link tracking thay người khác. Nay kiểm HMAC trên body gốc.
    raw_body = await request.body()
    verify_signature(raw_body, x_zalo_signature, get_settings().zalo_webhook_secret, "Zalo webhook")

    try:
        payload = ZaloWebhookRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    sender = payload.sender or {}
    zalo_user_id = sender.get("id")
    if not zalo_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu sender.id")

    zalo_service = ZaloService(db)

    if payload.token:
        try:
            linked_account = zalo_service.link_account(payload.token, zalo_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        db.commit()
        return {"status": "ZALO_LINKED", "user_id": linked_account.user_id}

    user_id = zalo_service.resolve_user_id(zalo_user_id)
    if user_id is None:
        return {"status": "ACCOUNT_NOT_LINKED", "user_id": None}

    message_text = ""
    if payload.message:
        message_text = str(payload.message.get("text") or payload.message.get("content") or "")

    shopee_url = find_shopee_url(message_text)
    if not shopee_url:
        return {"status": "NO_SHOPEE_URL", "user_id": user_id}

    link: AffiliateLink = AffiliateService(db, MockAffiliateProvider()).generate_link(user_id, shopee_url)
    db.commit()
    db.refresh(link)

    return {
        "status": "AFFILIATE_LINK_CREATED",
        "user_id": user_id,
        "affiliate_link_id": link.id,
        "tracking_id": link.tracking_id,
        "affiliate_url": link.affiliate_url,
    }
