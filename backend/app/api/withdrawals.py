from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import get_settings
from app.models.entities import User, Withdrawal
from app.schemas.common import WithdrawalCreateRequest, WithdrawalRead
from app.services.withdrawal_service import WithdrawalService

router = APIRouter(tags=["withdrawals"])


@router.post("", response_model=WithdrawalRead, status_code=status.HTTP_201_CREATED)
def create_withdrawal(
    payload: WithdrawalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Withdrawal:
    service = WithdrawalService(db, min_withdrawal_amount=get_settings().minimum_withdrawal_amount)
    try:
        withdrawal = service.request_withdrawal(
            user_id=current_user.id,
            amount=payload.amount,
            method=payload.method.value,
            bank_code=payload.bank_code,
            bank_name=payload.bank_name,
            account_name=payload.account_name,
            account_number=payload.account_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    db.refresh(withdrawal)
    return withdrawal


@router.get("", response_model=list[WithdrawalRead])
def list_withdrawals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Withdrawal]:
    return (
        db.query(Withdrawal)
        .filter(Withdrawal.user_id == current_user.id)
        .order_by(Withdrawal.requested_at.desc())
        .all()
    )