from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entities import AffiliateLink, CashbackTransaction, Order
from app.models.enums import CashbackStatus, CommissionStatus, OrderStatus
from app.providers.affiliate.base import AffiliateOrderPayload


class OrderService:
    def __init__(self, db: Session, cashback_rate_percent: Decimal = Decimal("0"), cashback_rate: Decimal | None = None):
        self.db = db
        self.cashback_rate = cashback_rate if cashback_rate is not None else cashback_rate_percent

    def calculate_cashback(self, commission_amount: Decimal) -> Decimal:
        return (commission_amount * self.cashback_rate / Decimal("100")).quantize(Decimal("0.01"))

    def attribute_order(self, payload: AffiliateOrderPayload) -> tuple[int | None, int | None, str]:
        if not payload.tracking_id:
            return None, None, OrderStatus.ATTRIBUTION_REVIEW.value

        link = self.db.query(AffiliateLink).filter(AffiliateLink.tracking_id == payload.tracking_id).one_or_none()
        if not link:
            return None, None, OrderStatus.ATTRIBUTION_REVIEW.value

        return link.user_id, link.id, payload.order_status

    def upsert_order_from_affiliate(self, payload: AffiliateOrderPayload) -> Order:
        existing = (
            self.db.query(Order)
            .filter(Order.platform == payload.platform, Order.platform_order_id == payload.platform_order_id)
            .one_or_none()
        )
        user_id, affiliate_link_id, order_status = self.attribute_order(payload)
        cashback_amount = self.calculate_cashback(payload.commission_amount) if user_id else Decimal("0")

        if existing:
            existing.tracking_id = payload.tracking_id
            existing.user_id = existing.user_id or user_id
            existing.affiliate_link_id = existing.affiliate_link_id or affiliate_link_id
            existing.product_id = payload.product_id
            existing.product_name = payload.product_name
            existing.order_amount = payload.order_amount
            existing.commission_amount = payload.commission_amount
            existing.cashback_rate = self.cashback_rate if existing.user_id else Decimal("0")
            existing.cashback_amount = cashback_amount if existing.user_id else Decimal("0")
            existing.currency = payload.currency
            existing.order_status = order_status if existing.order_status == OrderStatus.ATTRIBUTION_REVIEW.value else payload.order_status
            existing.commission_status = payload.commission_status
            if not user_id:
                existing.cashback_status = CashbackStatus.REVIEW.value
            elif self._cashback_is_eligible(payload.order_status, payload.commission_status):
                existing.cashback_status = CashbackStatus.PENDING.value
            else:
                existing.cashback_status = CashbackStatus.NONE.value
            existing.ordered_at = payload.ordered_at
            existing.completed_at = payload.completed_at
            self._ensure_pending_cashback(existing)
            self.db.flush()
            return existing

        order = Order(
            user_id=user_id,
            affiliate_link_id=affiliate_link_id,
            tracking_id=payload.tracking_id,
            platform=payload.platform,
            platform_order_id=payload.platform_order_id,
            product_id=payload.product_id,
            product_name=payload.product_name,
            order_amount=payload.order_amount,
            commission_amount=payload.commission_amount,
            cashback_rate=self.cashback_rate if user_id else Decimal("0"),
            cashback_amount=cashback_amount,
            currency=payload.currency,
            order_status=order_status,
            commission_status=payload.commission_status,
            cashback_status=(
                CashbackStatus.REVIEW.value
                if not user_id
                else (
                    CashbackStatus.PENDING.value
                    if self._cashback_is_eligible(payload.order_status, payload.commission_status)
                    else CashbackStatus.NONE.value
                )
            ),
            ordered_at=payload.ordered_at,
            completed_at=payload.completed_at,
        )
        self.db.add(order)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return (
                self.db.query(Order)
                .filter(Order.platform == payload.platform, Order.platform_order_id == payload.platform_order_id)
                .one()
            )
        self._ensure_pending_cashback(order)
        return order

    @staticmethod
    def _cashback_is_eligible(order_status: str, commission_status: str) -> bool:
        return (
            order_status in {
                OrderStatus.PENDING.value,
                OrderStatus.CONFIRMED.value,
                OrderStatus.COMPLETED.value,
            }
            and commission_status in {
                CommissionStatus.PENDING.value,
                CommissionStatus.CONFIRMED.value,
                CommissionStatus.SETTLED.value,
            }
        )

    def _ensure_pending_cashback(self, order: Order) -> None:
        if not order.user_id or order.cashback_status != CashbackStatus.PENDING.value:
            return
        already_recorded = (
            self.db.query(CashbackTransaction)
            .filter(
                CashbackTransaction.order_id == order.id,
                CashbackTransaction.transaction_type == "CASHBACK_PENDING",
            )
            .first()
        )
        if already_recorded:
            return
        from app.services.wallet_service import WalletService

        WalletService(self.db).add_pending_cashback(order.user_id, order.id, order.cashback_amount)