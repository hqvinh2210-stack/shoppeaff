from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.entities import CashbackTransaction, User
from app.schemas.common import TransactionRead, WalletRead
from app.services.wallet_service import WalletService

router = APIRouter(tags=["wallet"])


@router.get("", response_model=WalletRead)
def get_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = WalletService(db).get_or_create_wallet(current_user.id)
    db.commit()
    db.refresh(wallet)
    return wallet


@router.get("/transactions", response_model=list[TransactionRead])
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CashbackTransaction]:
    return (
        db.query(CashbackTransaction)
        .filter(CashbackTransaction.user_id == current_user.id)
        .order_by(CashbackTransaction.created_at.desc())
        .all()
    )