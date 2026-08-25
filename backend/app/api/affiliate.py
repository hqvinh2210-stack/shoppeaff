from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.core.webhook_security import verify_shared_secret, verify_signature
from app.models.entities import AffiliateLink, Order, User, WebhookIdempotencyKey
from app.providers.affiliate.shopee import MockAffiliateProvider
from app.providers.affiliate.accesstrade import AccessTradeClient
from app.services.accesstrade_service import AccessTradeService
from app.schemas.common import AffiliateGenerateRequest, AffiliateLinkRead, AffiliateWebhookRequest, OrderRead
from app.services.affiliate_service import AffiliateService
from app.services.order_service import OrderService

router = APIRouter(tags=["affiliate"])


@router.post("/generate-link", response_model=AffiliateLinkRead, status_code=status.HTTP_201_CREATED)
def generate_link(
    payload: AffiliateGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AffiliateLink:
    service = AffiliateService(db, MockAffiliateProvider())
    link = service.generate_link(current_user.id, payload.original_url)
    db.commit()
    db.refresh(link)
    return link


@router.post("/accesstrade/link", status_code=status.HTTP_201_CREATED)
def generate_accesstrade_link(
    payload: AffiliateGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.accesstrade_api_token or not settings.accesstrade_campaign_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AccessTrade is not configured")
    client = AccessTradeClient(settings.accesstrade_api_token, settings.accesstrade_base_url, settings.accesstrade_timeout_seconds)
    try:
        click = AccessTradeService(db, client).create_click(current_user.id, settings.accesstrade_campaign_id, payload.original_url)
        db.commit()
        return {"tracking_id": click.tracking_id, "affiliate_url": click.aff_link, "short_url": click.short_link, "url_origin": click.url_origin}
    finally:
        client.close()


@router.get("/links", response_model=list[AffiliateLinkRead])
def list_links(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AffiliateLink]:
    return (
        db.query(AffiliateLink)
        .filter(AffiliateLink.user_id == current_user.id)
        .order_by(AffiliateLink.id.desc())
        .all()
    )


@router.post("/webhook", response_model=list[OrderRead])
async def affiliate_webhook(
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    signature: str | None = Header(default=None, alias="X-Affiliate-Signature"),
    shared_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> list:
    # Endpoint này ghi thẳng vào ví người dùng nên phải xác thực trước khi parse.
    # Ưu tiên chữ ký HMAC; chấp nhận bí mật dùng chung cho mạng affiliate chưa
    # hỗ trợ ký. Không có cái nào hợp lệ thì dừng ngay tại đây.
    settings = get_settings()
    raw_body = await request.body()
    if signature is not None:
        verify_signature(raw_body, signature, settings.affiliate_webhook_secret, "Affiliate webhook")
    else:
        verify_shared_secret(shared_secret, settings.affiliate_webhook_secret, "Affiliate webhook")

    try:
        payload = AffiliateWebhookRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    effective_idempotency_key = idempotency_key or payload.idempotency_key
    if effective_idempotency_key is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key is required")

    stored_key = db.query(WebhookIdempotencyKey).filter(WebhookIdempotencyKey.key == effective_idempotency_key).one_or_none()
    if stored_key:
        order_ids = [int(order_id) for order_id in stored_key.order_ids.split(",") if order_id]
        return db.query(Order).filter(Order.id.in_(order_ids)).order_by(Order.id).all()

    service = OrderService(db, cashback_rate_percent=get_settings().cashback_rate_percent)
    orders = [service.upsert_order_from_affiliate(order_payload) for order_payload in payload.orders]
    db.add(WebhookIdempotencyKey(key=effective_idempotency_key, order_ids=','.join(str(order.id) for order in orders)))
    db.commit()
    for order in orders:
        db.refresh(order)
    return orders