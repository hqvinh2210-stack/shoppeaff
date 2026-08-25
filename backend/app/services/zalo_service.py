from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.models.entities import ZaloAccount, ZaloLinkToken
from app.models.enums import LinkStatus


class ZaloService:
    def __init__(self, db: Session):
        self.db = db

    def create_link_token(self, user_id: int, ttl_minutes: int = 15) -> ZaloLinkToken:
        link_token = ZaloLinkToken(
            user_id=user_id,
            token=token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            status=LinkStatus.ACTIVE.value,
        )
        self.db.add(link_token)
        self.db.flush()
        return link_token

    def resolve_user_id(self, zalo_user_id: str) -> int | None:
        account = (
            self.db.query(ZaloAccount)
            .filter(ZaloAccount.zalo_user_id == zalo_user_id, ZaloAccount.status == LinkStatus.ACTIVE.value)
            .one_or_none()
        )
        return account.user_id if account else None

    def link_account(self, token: str, zalo_user_id: str, user_external_id: str | None = None) -> ZaloAccount:
        now = datetime.now(timezone.utc)
        link_token = (
            self.db.query(ZaloLinkToken)
            .filter(ZaloLinkToken.token == token, ZaloLinkToken.status == LinkStatus.ACTIVE.value)
            .one_or_none()
        )
        if not link_token:
            raise ValueError("Invalid Zalo linking token")
        # Ensure link_token.expires_at is timezone-aware for comparison
        expires_at_aware = link_token.expires_at
        if expires_at_aware.tzinfo is None:
            expires_at_aware = expires_at_aware.replace(tzinfo=timezone.utc)

        if link_token.used_at is not None or expires_at_aware < now:
            link_token.status = LinkStatus.EXPIRED.value
            raise ValueError("Expired or used Zalo linking token")

        existing_zalo = self.db.query(ZaloAccount).filter(ZaloAccount.zalo_user_id == zalo_user_id).one_or_none()
        if existing_zalo and existing_zalo.user_id != link_token.user_id:
            raise ValueError("This Zalo account is already linked to another user")

        active_for_user = (
            self.db.query(ZaloAccount)
            .filter(ZaloAccount.user_id == link_token.user_id, ZaloAccount.status == LinkStatus.ACTIVE.value)
            .one_or_none()
        )
        if active_for_user and active_for_user.zalo_user_id != zalo_user_id:
            raise ValueError("User already has an active Zalo account")

        account = existing_zalo or ZaloAccount(
            user_id=link_token.user_id,
            zalo_user_id=zalo_user_id,
            user_external_id=user_external_id,
            status=LinkStatus.ACTIVE.value,
        )
        account.user_id = link_token.user_id
        account.user_external_id = user_external_id
        account.status = LinkStatus.ACTIVE.value
        account.linked_at = now

        link_token.used_at = now
        link_token.status = LinkStatus.USED.value
        self.db.add(account)
        self.db.flush()
        return account