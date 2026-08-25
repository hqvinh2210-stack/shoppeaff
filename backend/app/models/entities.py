from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    AffiliatePlatform,
    CashbackStatus,
    CommissionStatus,
    LinkStatus,
    OrderStatus,
    TransactionStatus,
    TransactionType,
    UserStatus,
    WithdrawalStatus,
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    full_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default=UserStatus.ACTIVE.value, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="USER", nullable=False)

    zalo_accounts: Mapped[list["ZaloAccount"]] = relationship(back_populates="user")
    telegram_accounts: Mapped[list["TelegramAccount"]] = relationship(back_populates="user")
    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)
    affiliate_links: Mapped[list["AffiliateLink"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class ZaloAccount(Base):
    __tablename__ = "zalo_accounts"
    __table_args__ = (
        UniqueConstraint("zalo_user_id", name="uq_zalo_accounts_zalo_user_id"),
        Index("ix_zalo_accounts_one_active_per_user", "user_id", "status", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    zalo_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_external_id: Mapped[str | None] = mapped_column(String(255))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=LinkStatus.ACTIVE.value, nullable=False)

    user: Mapped[User] = relationship(back_populates="zalo_accounts")


class ZaloLinkToken(Base):
    __tablename__ = "zalo_link_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=LinkStatus.ACTIVE.value, nullable=False)


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    __table_args__ = (
        UniqueConstraint("telegram_user_id", name="uq_telegram_accounts_user_id"),
        Index("ix_telegram_accounts_one_active_per_user", "user_id", "status", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=LinkStatus.ACTIVE.value, nullable=False)

    user: Mapped[User] = relationship(back_populates="telegram_accounts")


class TelegramLinkToken(Base):
    __tablename__ = "telegram_link_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=LinkStatus.ACTIVE.value, nullable=False)


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="wallet")


class AffiliateLink(Base):
    __tablename__ = "affiliate_links"
    __table_args__ = (UniqueConstraint("tracking_id", name="uq_affiliate_links_tracking_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[str | None] = mapped_column(String(128))
    shop_id: Mapped[str | None] = mapped_column(String(128))
    affiliate_url: Mapped[str | None] = mapped_column(Text)
    tracking_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default=AffiliatePlatform.SHOPEE.value, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=LinkStatus.ACTIVE.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="affiliate_links")
    orders: Mapped[list["Order"]] = relationship(back_populates="affiliate_link")


class AffiliateClick(Base, TimestampMixin):
    __tablename__ = "affiliate_clicks"
    __table_args__ = (UniqueConstraint("tracking_id", name="uq_affiliate_clicks_tracking_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tracking_id: Mapped[str] = mapped_column(String(128), nullable=False)
    network: Mapped[str] = mapped_column(String(32), default="ACCESSTRADE", nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(128), nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(128))
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    aff_link: Mapped[str | None] = mapped_column(Text)
    short_link: Mapped[str | None] = mapped_column(Text)
    url_origin: Mapped[str | None] = mapped_column(Text)
    utm_source: Mapped[str | None] = mapped_column(String(128))
    utm_medium: Mapped[str | None] = mapped_column(String(128))
    utm_campaign: Mapped[str | None] = mapped_column(String(128))
    utm_content: Mapped[str | None] = mapped_column(String(128))
    sub1: Mapped[str] = mapped_column(String(128), nullable=False)
    sub2: Mapped[str | None] = mapped_column(String(128))
    sub3: Mapped[str | None] = mapped_column(String(128))
    sub4: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)


class AffiliateOrder(Base, TimestampMixin):
    __tablename__ = "affiliate_orders"
    __table_args__ = (UniqueConstraint("network", "merchant", "external_order_id", name="uq_affiliate_orders_external"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    merchant: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    tracking_id: Mapped[str | None] = mapped_column(String(128))
    billing: Mapped[dict | None] = mapped_column(JSON)
    commission: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    order_pending: Mapped[dict | None] = mapped_column(JSON)
    order_approved: Mapped[dict | None] = mapped_column(JSON)
    order_reject: Mapped[dict | None] = mapped_column(JSON)
    products_count: Mapped[int | None] = mapped_column(Integer)
    click_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sales_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    update_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    at_product_link: Mapped[str | None] = mapped_column(Text)
    utm_source: Mapped[str | None] = mapped_column(String(128))
    utm_medium: Mapped[str | None] = mapped_column(String(128))
    utm_campaign: Mapped[str | None] = mapped_column(String(128))
    utm_content: Mapped[str | None] = mapped_column(String(128))
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)


class AffiliateOrderItem(Base):
    __tablename__ = "affiliate_order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    affiliate_order_id: Mapped[int] = mapped_column(ForeignKey("affiliate_orders.id"), nullable=False)
    external_item_id: Mapped[str | None] = mapped_column(String(128))
    campaign_id: Mapped[str | None] = mapped_column(String(128))
    product_id: Mapped[str | None] = mapped_column(String(128))
    product_name: Mapped[str | None] = mapped_column(String(500))
    product_category: Mapped[str | None] = mapped_column(String(255))
    product_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    product_quantity: Mapped[dict | None] = mapped_column(JSON)
    billing_pending: Mapped[dict | None] = mapped_column(JSON)
    billing_approved: Mapped[dict | None] = mapped_column(JSON)
    billing_reject: Mapped[dict | None] = mapped_column(JSON)
    commission_pending: Mapped[dict | None] = mapped_column(JSON)
    commission_approved: Mapped[dict | None] = mapped_column(JSON)
    commission_reject: Mapped[dict | None] = mapped_column(JSON)
    reason_rejected: Mapped[str | None] = mapped_column(Text)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)


class AffiliateTransaction(Base, TimestampMixin):
    __tablename__ = "affiliate_transactions"
    __table_args__ = (UniqueConstraint("network", "merchant", "transaction_id", "product_id", name="uq_affiliate_transactions_external"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant: Mapped[str] = mapped_column(String(128), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    conversion_id: Mapped[str | None] = mapped_column(String(128))
    affiliate_order_id: Mapped[int | None] = mapped_column(ForeignKey("affiliate_orders.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    tracking_id: Mapped[str | None] = mapped_column(String(128))
    product_id: Mapped[str | None] = mapped_column(String(128))
    product_name: Mapped[str | None] = mapped_column(String(500))
    product_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    product_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    transaction_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    commission: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    status: Mapped[int] = mapped_column(Integer, nullable=False)
    is_confirmed: Mapped[int | None] = mapped_column(Integer)
    click_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    update_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason_rejected: Mapped[str | None] = mapped_column(Text)
    is_brand_bonus: Mapped[bool | None] = mapped_column()
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)


class UnmatchedAffiliateOrder(Base):
    __tablename__ = "unmatched_affiliate_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant: Mapped[str] = mapped_column(String(128), nullable=False)
    external_order_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tracking_value: Mapped[str | None] = mapped_column(String(255))
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("platform", "platform_order_id", name="uq_orders_platform_order_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    affiliate_link_id: Mapped[int | None] = mapped_column(ForeignKey("affiliate_links.id"))
    tracking_id: Mapped[str | None] = mapped_column(String(128))

    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_order_id: Mapped[str] = mapped_column(String(128), nullable=False)

    product_id: Mapped[str | None] = mapped_column(String(128))
    product_name: Mapped[str | None] = mapped_column(String(500))

    order_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    cashback_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False)
    cashback_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="VND", nullable=False)

    order_status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING.value, nullable=False)
    commission_status: Mapped[str] = mapped_column(String(32), default=CommissionStatus.PENDING.value, nullable=False)
    cashback_status: Mapped[str] = mapped_column(String(32), default=CashbackStatus.NONE.value, nullable=False)

    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User | None] = relationship(back_populates="orders")
    affiliate_link: Mapped[AffiliateLink | None] = relationship(back_populates="orders")


class CashbackTransaction(Base):
    __tablename__ = "cashback_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    affiliate_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("affiliate_transactions.id"))
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TransactionStatus.COMPLETED.value, nullable=False)
    reference_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WebhookIdempotencyKey(Base):
    __tablename__ = "webhook_idempotency_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    order_ids: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    # Ngân hàng nhận tiền. Chỉ bắt buộc khi method = BANK; ví điện tử để trống.
    bank_code: Mapped[str | None] = mapped_column(String(32))
    bank_name: Mapped[str | None] = mapped_column(String(255))
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=WithdrawalStatus.PENDING.value, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(128))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
