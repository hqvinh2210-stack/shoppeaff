from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.models.entities import TelegramAccount, TelegramLinkToken
from app.models.enums import LinkStatus


class TelegramService:
    def __init__(self, db: Session):
        self.db = db

    def create_link_token(self, user_id: int, ttl_minutes: int = 15) -> TelegramLinkToken:
        token = TelegramLinkToken(
            user_id=user_id,
            token=token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            status=LinkStatus.ACTIVE.value,
        )
        self.db.add(token)
        self.db.flush()
        return token

    def link_account(self, token: str, telegram_user_id: str) -> TelegramAccount:
        now = datetime.now(timezone.utc)
        link_token = self.db.query(TelegramLinkToken).filter(
            TelegramLinkToken.token == token,
            TelegramLinkToken.status == LinkStatus.ACTIVE.value,
        ).one_or_none()
        if not link_token:
            raise ValueError("Invalid Telegram linking token")
        expires_at = link_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if link_token.used_at is not None or expires_at < now:
            link_token.status = LinkStatus.EXPIRED.value
            raise ValueError("Expired or used Telegram linking token")

        existing = self.db.query(TelegramAccount).filter(TelegramAccount.telegram_user_id == telegram_user_id).one_or_none()
        if existing and existing.user_id != link_token.user_id:
            raise ValueError("This Telegram account is already linked to another user")
        active = self.db.query(TelegramAccount).filter(
            TelegramAccount.user_id == link_token.user_id,
            TelegramAccount.status == LinkStatus.ACTIVE.value,
        ).one_or_none()
        if active and active.telegram_user_id != telegram_user_id:
            raise ValueError("User already has an active Telegram account")

        account = existing or TelegramAccount(user_id=link_token.user_id, telegram_user_id=telegram_user_id)
        account.user_id = link_token.user_id
        account.status = LinkStatus.ACTIVE.value
        account.linked_at = now
        link_token.used_at = now
        link_token.status = LinkStatus.USED.value
        self.db.add(account)
        self.db.flush()
        return account

    def resolve_user_id(self, telegram_user_id: str) -> int | None:
        account = self.db.query(TelegramAccount).filter(
            TelegramAccount.telegram_user_id == telegram_user_id,
            TelegramAccount.status == LinkStatus.ACTIVE.value,
        ).one_or_none()
        return account.user_id if account else None