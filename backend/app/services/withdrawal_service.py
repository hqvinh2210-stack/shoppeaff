from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.entities import Withdrawal
from app.models.enums import WithdrawalStatus
from app.services.wallet_service import WalletService


class WithdrawalService:
    def __init__(self, db: Session, min_withdrawal_amount: Decimal):
        self.db = db
        self.minimum_withdrawal_amount = min_withdrawal_amount
        self.wallet_service = WalletService(db)

    def request_withdrawal(
        self,
        user_id: int,
        amount: Decimal,
        method: str,
        account_name: str,
        account_number: str,
        bank_code: str | None = None,
        bank_name: str | None = None,
    ) -> Withdrawal:
        if amount < self.minimum_withdrawal_amount:
            raise ValueError(
                f"Số tiền rút tối thiểu là {self.minimum_withdrawal_amount:,.0f}đ"
            )

        self.wallet_service.reserve_withdrawal(user_id=user_id, amount=amount)

        withdrawal = Withdrawal(
            user_id=user_id,
            amount=amount,
            method=method,
            bank_code=bank_code,
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            status=WithdrawalStatus.PENDING.value,
        )
        self.db.add(withdrawal)
        self.db.flush()
        return withdrawal

    def reject_withdrawal(self, withdrawal: Withdrawal, reason: str) -> Withdrawal:
        if withdrawal.status in (WithdrawalStatus.REJECTED.value, WithdrawalStatus.COMPLETED.value):
            return withdrawal
        self.wallet_service.reject_withdrawal(
            user_id=withdrawal.user_id,
            amount=withdrawal.amount,
            reference_code=f"WDR-{withdrawal.id}",
        )
        withdrawal.status = WithdrawalStatus.REJECTED.value
        withdrawal.rejection_reason = reason
        self.db.flush()
        return withdrawal