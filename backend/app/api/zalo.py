from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.entities import User, ZaloAccount
from app.schemas.common import ZaloLinkResponse, ZaloStatusResponse
from app.services.zalo_service import ZaloService

router = APIRouter(tags=["zalo"])


@router.post("/zalo/link", response_model=ZaloLinkResponse)
def create_zalo_link(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ZaloLinkResponse:
    token = ZaloService(db).create_link_token(current_user.id)
    db.commit()
    return ZaloLinkResponse(
        token=token.token,
        expires_at=token.expires_at,
        link_url=f"https://zalo.me/oa?link_token={token.token}",
    )


@router.get("/zalo/status", response_model=ZaloStatusResponse)
def get_zalo_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ZaloStatusResponse:
    account = (
        db.query(ZaloAccount)
        .filter(ZaloAccount.user_id == current_user.id, ZaloAccount.status == "ACTIVE")
        .one_or_none()
    )
    if account is None:
        return ZaloStatusResponse(linked=False)
    return ZaloStatusResponse(linked=True, zalo_user_id=account.zalo_user_id, status=account.status)


@router.delete("/zalo/unlink", status_code=status.HTTP_204_NO_CONTENT)
def unlink_zalo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    account = (
        db.query(ZaloAccount)
        .filter(ZaloAccount.user_id == current_user.id, ZaloAccount.status == "ACTIVE")
        .one_or_none()
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active Zalo account linked")
    account.status = "INACTIVE"
    db.commit()