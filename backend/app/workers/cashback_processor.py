from sqlalchemy.orm import Session

from app.models.entities import Order
from app.models.enums import CashbackStatus, CommissionStatus, OrderStatus
from app.services.wallet_service import WalletService


def approve_cashback(db: Session) -> int:
    """
    Move settled completed order cashback from pending to available balance.

    This job preserves the non-negotiable ledger rule by delegating all balance
    changes to WalletService, which creates immutable cashback_transactions.
    """
    wallet_service = WalletService(db)
    approved_count = 0

    orders = (
        db.query(Order)
        .filter(Order.order_status == OrderStatus.COMPLETED.value)
        .filter(Order.commission_status == CommissionStatus.SETTLED.value)
        .filter(Order.cashback_status == CashbackStatus.PENDING.value)
        .all()
    )

    for order in orders:
        wallet_service.approve_cashback(order.user_id, order.id, order.cashback_amount)
        approved_count += 1

    db.commit()
    return approved_count