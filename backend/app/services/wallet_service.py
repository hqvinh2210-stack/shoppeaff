from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.entities import CashbackTransaction, Order, Wallet
from app.models.enums import CashbackStatus, TransactionStatus, TransactionType


class WalletService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_wallet(self, user_id: int, currency: str = "VND") -> Wallet:
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).one_or_none()
        if wallet:
            return wallet
        wallet = Wallet(user_id=user_id, available_balance=Decimal("0"), pending_balance=Decimal("0"), currency=currency)
        self.db.add(wallet)
        self.db.flush()
        return wallet

    def add_pending_cashback(self, user_id: int, order_id: int | None, amount: Decimal, affiliate_transaction_id: int | None = None) -> CashbackTransaction:
        wallet = self.get_or_create_wallet(user_id)
        before = wallet.pending_balance
        wallet.pending_balance += amount
        tx = CashbackTransaction(
            user_id=user_id,
            order_id=order_id,
            affiliate_transaction_id=affiliate_transaction_id,
            transaction_type=TransactionType.CASHBACK_PENDING.value,
            amount=amount,
            balance_before=before,
            balance_after=wallet.pending_balance,
            status=TransactionStatus.PENDING.value,
            reference_code=f"CBP-{order_id}-{uuid4().hex[:12]}",
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def approve_cashback(self, user_id: int, order_id: int | None, amount: Decimal, affiliate_transaction_id: int | None = None) -> CashbackTransaction:
        existing = (
            self.db.query(CashbackTransaction)
            .filter(
                CashbackTransaction.order_id == order_id,
                CashbackTransaction.affiliate_transaction_id == affiliate_transaction_id,
                CashbackTransaction.transaction_type == TransactionType.CASHBACK_APPROVED.value,
            )
            .first()
        )
        if existing:
            return existing
        wallet = self.get_or_create_wallet(user_id)
        if wallet.pending_balance < amount:
            raise ValueError("Insufficient pending balance to approve cashback")
        before = wallet.available_balance
        wallet.pending_balance -= amount
        wallet.available_balance += amount
        tx = CashbackTransaction(
            user_id=user_id,
            order_id=order_id,
            affiliate_transaction_id=affiliate_transaction_id,
            transaction_type=TransactionType.CASHBACK_APPROVED.value,
            amount=amount,
            balance_before=before,
            balance_after=wallet.available_balance,
            status=TransactionStatus.COMPLETED.value,
            reference_code=f"CBA-{order_id}-{uuid4().hex[:12]}",
        )
        self.db.add(tx)
        # Update the associated order's cashback status to APPROVED
        order = self.db.query(Order).filter(Order.id == order_id).one_or_none()
        if order:
            order.cashback_status = CashbackStatus.APPROVED.value
        self.db.flush()
        return tx

    def reject_withdrawal(self, user_id: int, amount: Decimal, reference_code: str) -> CashbackTransaction:
        wallet = self.get_or_create_wallet(user_id)
        before = wallet.available_balance
        wallet.available_balance += amount
        tx = CashbackTransaction(
            user_id=user_id,
            transaction_type=TransactionType.WITHDRAWAL_REJECTED.value,
            amount=amount,
            balance_before=before,
            balance_after=wallet.available_balance,
            status=TransactionStatus.COMPLETED.value,
            reference_code=f"{reference_code}-REJECTED",
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    def reserve_withdrawal(self, user_id: int, amount: Decimal) -> CashbackTransaction:
        wallet = self.get_or_create_wallet(user_id)
        if amount <= 0:
            raise ValueError("Số tiền rút phải lớn hơn 0")
        if wallet.available_balance < amount:
            raise ValueError("Số tiền rút vượt quá số dư khả dụng")
        before = wallet.available_balance
        wallet.available_balance -= amount
        tx = CashbackTransaction(
            user_id=user_id,
            transaction_type=TransactionType.WITHDRAWAL.value,
            amount=-amount,
            balance_before=before,
            balance_after=wallet.available_balance,
            status=TransactionStatus.PENDING.value,
            reference_code=f"WDR-{uuid4().hex[:16]}",
        )
        self.db.add(tx)
        self.db.flush()
        return tx