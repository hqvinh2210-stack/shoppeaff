from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.entities import AffiliateTransaction, CashbackTransaction
from app.models.enums import TransactionStatus, TransactionType
from app.services.wallet_service import WalletService


class CashbackReconciliationService:
    def __init__(self, db: Session, cashback_rate_percent: Decimal):
        self.db = db
        self.rate = cashback_rate_percent
        self.wallet = WalletService(db)

    def process_transaction(self, transaction: AffiliateTransaction) -> CashbackTransaction | None:
        if transaction.user_id is None or transaction.commission is None:
            return None
        amount = (transaction.commission * self.rate / Decimal("100")).quantize(Decimal("0.01"))
        approved = self._find(transaction.id, TransactionType.CASHBACK_APPROVED.value)
        reversed_tx = self._find(transaction.id, TransactionType.CASHBACK_REVERSED.value)
        if transaction.status == 2:
            if approved and not reversed_tx:
                return self._reverse(transaction, amount)
            return None
        if transaction.status != 1 or transaction.is_confirmed not in (None, 1):
            return self._ensure_pending(transaction, amount)
        if approved:
            return approved
        pending = self._find(transaction.id, TransactionType.CASHBACK_PENDING.value)
        if not pending:
            self.wallet.add_pending_cashback(transaction.user_id, None, amount, transaction.id)
        approved = self.wallet.approve_cashback(transaction.user_id, None, amount, transaction.id)
        approved.affiliate_transaction_id = transaction.id
        self.db.flush()
        return approved

    def _find(self, transaction_id: int, transaction_type: str) -> CashbackTransaction | None:
        return self.db.query(CashbackTransaction).filter_by(
            affiliate_transaction_id=transaction_id, transaction_type=transaction_type
        ).one_or_none()

    def _ensure_pending(self, transaction: AffiliateTransaction, amount: Decimal) -> CashbackTransaction:
        pending = self._find(transaction.id, TransactionType.CASHBACK_PENDING.value)
        if pending:
            return pending
        tx = self.wallet.add_pending_cashback(transaction.user_id, None, amount, transaction.id)
        tx.affiliate_transaction_id = transaction.id
        return tx

    def _reverse(self, transaction: AffiliateTransaction, amount: Decimal) -> CashbackTransaction:
        wallet = self.wallet.get_or_create_wallet(transaction.user_id)
        if wallet.available_balance < amount:
            raise ValueError("Cannot reverse cashback beyond available balance")
        before = wallet.available_balance
        wallet.available_balance -= amount
        tx = CashbackTransaction(
            user_id=transaction.user_id,
            affiliate_transaction_id=transaction.id,
            transaction_type=TransactionType.CASHBACK_REVERSED.value,
            amount=-amount,
            balance_before=before,
            balance_after=wallet.available_balance,
            status=TransactionStatus.REVERSED.value,
            reference_code=f"CBR-AT-{transaction.id}",
        )
        self.db.add(tx)
        self.db.flush()
        return tx