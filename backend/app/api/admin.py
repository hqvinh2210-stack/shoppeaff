from decimal import Decimal

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.entities import AuditLog, CashbackTransaction, Order, User, Wallet, Withdrawal
from app.models.enums import OrderStatus, WithdrawalStatus
from app.services.withdrawal_service import WithdrawalService

router = APIRouter(tags=["admin"])


class CashbackRateRequest(BaseModel):
    cashback_rate_percent: Decimal = Field(ge=0, le=100)


class RejectWithdrawalRequest(BaseModel):
    # Nhận qua body thay vì query string cho đồng nhất với mọi endpoint POST khác.
    reason: str = Field(min_length=3, max_length=500)


_FINAL_WITHDRAWAL_STATUSES = {
    WithdrawalStatus.COMPLETED.value,
    WithdrawalStatus.REJECTED.value,
}


def _get_withdrawal(db: Session, withdrawal_id: int) -> Withdrawal:
    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).one_or_none()
    if withdrawal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy yêu cầu rút tiền")
    return withdrawal


def _audit(
    db: Session,
    admin: User,
    action: str,
    entity_id: int,
    old_value: str | None,
    new_value: str | None,
) -> None:
    """Ghi vết mọi thao tác quản trị chạm vào tiền của người dùng."""
    db.add(
        AuditLog(
            user_id=admin.id,
            action=action,
            entity_type="withdrawal",
            entity_id=str(entity_id),
            old_value=old_value,
            new_value=new_value,
        )
    )


@router.get("/users")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(User, Wallet)
        .outerjoin(Wallet, Wallet.user_id == User.id)
        .order_by(User.id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": user.id,
            "user_code": user.user_code,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
            "available_balance": wallet.available_balance if wallet else 0,
            "pending_balance": wallet.pending_balance if wallet else 0,
            "created_at": user.created_at,
        }
        for user, wallet in rows
    ]


@router.get("/orders")
def list_orders(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(500).all()
    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "platform": order.platform,
            "platform_order_id": order.platform_order_id,
            "tracking_id": order.tracking_id,
            "order_status": order.order_status,
            "commission_status": order.commission_status,
            "cashback_status": order.cashback_status,
            "cashback_amount": order.cashback_amount,
        }
        for order in orders
    ]


@router.get("/cashback/monthly")
def monthly_cashback_summary(
    year: int = Query(ge=2020, le=2100),
    month: int = Query(ge=1, le=12),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)
    approved_type = "CASHBACK_APPROVED"
    reversed_type = "CASHBACK_REVERSED"
    rows = db.query(
        CashbackTransaction.user_id,
        func.coalesce(func.sum(CashbackTransaction.amount), 0).label("net_cashback"),
        func.count(CashbackTransaction.id).label("transactions"),
    ).filter(
        CashbackTransaction.transaction_type.in_([approved_type, reversed_type]),
        CashbackTransaction.created_at >= start,
        CashbackTransaction.created_at < end,
    ).group_by(CashbackTransaction.user_id).all()
    total = sum((row.net_cashback for row in rows), 0)
    return {
        "year": year,
        "month": month,
        "total_cashback": total,
        "users": [{"user_id": row.user_id, "net_cashback": row.net_cashback, "transactions": row.transactions} for row in rows],
    }


@router.get("/withdrawals")
def list_withdrawals(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    withdrawals = db.query(Withdrawal).order_by(Withdrawal.requested_at.desc()).limit(500).all()
    return [
        {
            "id": withdrawal.id,
            "user_id": withdrawal.user_id,
            "amount": withdrawal.amount,
            "method": withdrawal.method,
            # Admin cần đủ thông tin để chuyển khoản ngay trên màn hình duyệt.
            "bank_code": withdrawal.bank_code,
            "bank_name": withdrawal.bank_name,
            "account_name": withdrawal.account_name,
            "account_number": withdrawal.account_number,
            "status": withdrawal.status,
            "requested_at": withdrawal.requested_at,
            "processed_at": withdrawal.processed_at,
            "rejection_reason": withdrawal.rejection_reason,
        }
        for withdrawal in withdrawals
    ]


@router.get("/summary")
def operations_summary(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    """Các con số cần liếc qua đầu ca trực: việc đang chờ xử lý và tổng tồn ví."""
    balances = db.query(
        func.coalesce(func.sum(Wallet.available_balance), 0),
        func.coalesce(func.sum(Wallet.pending_balance), 0),
    ).one()
    return {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "pending_withdrawals": db.query(func.count(Withdrawal.id))
        .filter(Withdrawal.status.in_([WithdrawalStatus.PENDING.value, WithdrawalStatus.PROCESSING.value]))
        .scalar()
        or 0,
        "attribution_review_orders": db.query(func.count(Order.id))
        .filter(Order.order_status == OrderStatus.ATTRIBUTION_REVIEW.value)
        .scalar()
        or 0,
        "total_available_balance": balances[0],
        "total_pending_balance": balances[1],
    }


@router.get("/orders/attribution-review")
def list_attribution_review_orders(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    orders = (
        db.query(Order)
        .filter(Order.order_status == OrderStatus.ATTRIBUTION_REVIEW.value)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [
        {
            "id": order.id,
            "platform": order.platform,
            "platform_order_id": order.platform_order_id,
            "tracking_id": order.tracking_id,
            "commission_amount": order.commission_amount,
            "cashback_status": order.cashback_status,
        }
        for order in orders
    ]


@router.post("/cashback-rates")
def set_cashback_rate(_: CashbackRateRequest, __: User = Depends(require_admin)) -> dict[str, str]:
    return {
        "status": "CONFIG_ACCEPTED",
        "note": "Persist this value in deployment configuration or a dedicated settings table before production use.",
    }


@router.post("/withdrawals/{withdrawal_id}/approve")
def approve_withdrawal(withdrawal_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict[str, str | int]:
    withdrawal = _get_withdrawal(db, withdrawal_id)
    if withdrawal.status in _FINAL_WITHDRAWAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Yêu cầu đã ở trạng thái cuối ({withdrawal.status}), không đổi được nữa",
        )
    previous = withdrawal.status
    withdrawal.status = WithdrawalStatus.COMPLETED.value
    withdrawal.processed_at = datetime.now(timezone.utc)
    _audit(db, admin, "WITHDRAWAL_APPROVE", withdrawal.id, previous, withdrawal.status)
    db.commit()
    return {"status": "WITHDRAWAL_APPROVED", "withdrawal_id": withdrawal.id}


@router.post("/withdrawals/{withdrawal_id}/reject")
def reject_withdrawal(
    withdrawal_id: int,
    payload: RejectWithdrawalRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    withdrawal = _get_withdrawal(db, withdrawal_id)
    if withdrawal.status in _FINAL_WITHDRAWAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Yêu cầu đã ở trạng thái cuối ({withdrawal.status}), không đổi được nữa",
        )
    previous = withdrawal.status
    # Từ chối phải hoàn tiền đã giữ về ví — luôn đi qua service để sinh bản ghi
    # sổ cái, không bao giờ sửa số dư trực tiếp.
    WithdrawalService(db, min_withdrawal_amount=Decimal("0")).reject_withdrawal(withdrawal, payload.reason)
    withdrawal.processed_at = datetime.now(timezone.utc)
    _audit(db, admin, "WITHDRAWAL_REJECT", withdrawal.id, previous, payload.reason)
    db.commit()
    return {"status": "WITHDRAWAL_REJECTED", "withdrawal_id": withdrawal.id}