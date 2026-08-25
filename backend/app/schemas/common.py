from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import WithdrawalMethod


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: str | None = None
    phone: str | None = None
    password: str = Field(min_length=8)
    full_name: str | None = None


class LoginRequest(BaseModel):
    identifier: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20)


class UserRead(ORMModel):
    id: int
    user_code: str
    email: str | None
    phone: str | None
    full_name: str | None
    status: str
    # Frontend cần `role` để ẩn/hiện tab quản trị. 403 vẫn là lớp chặn thật sự,
    # trường này chỉ để giao diện không mời gọi thao tác chắc chắn bị từ chối.
    role: str
    created_at: datetime


class ZaloLinkResponse(BaseModel):
    token: str
    expires_at: datetime
    link_url: str


class ZaloStatusResponse(BaseModel):
    linked: bool
    zalo_user_id: str | None = None
    status: str | None = None


class AffiliateGenerateRequest(BaseModel):
    original_url: str


class AffiliateLinkRead(ORMModel):
    id: int
    user_id: int
    original_url: str
    normalized_url: str
    product_id: str | None
    shop_id: str | None
    affiliate_url: str | None
    tracking_id: str
    platform: str
    status: str
    created_at: datetime


class OrderRead(ORMModel):
    id: int
    user_id: int | None
    affiliate_link_id: int | None
    tracking_id: str | None
    platform: str
    platform_order_id: str
    product_id: str | None
    product_name: str | None
    order_amount: Decimal
    commission_amount: Decimal
    cashback_rate: Decimal
    cashback_amount: Decimal
    currency: str
    order_status: str
    commission_status: str
    cashback_status: str
    ordered_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class WalletRead(ORMModel):
    available_balance: Decimal
    pending_balance: Decimal
    currency: str
    updated_at: datetime


class TransactionRead(ORMModel):
    id: int
    order_id: int | None
    transaction_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    status: str
    reference_code: str
    created_at: datetime


class WithdrawalCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: WithdrawalMethod
    bank_code: str | None = Field(default=None, max_length=32)
    bank_name: str | None = Field(default=None, max_length=255)
    account_name: str = Field(min_length=2, max_length=255)
    account_number: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def require_bank_for_bank_transfer(self) -> "WithdrawalCreateRequest":
        if self.method is WithdrawalMethod.BANK and not self.bank_code:
            raise ValueError("Chuyển khoản ngân hàng bắt buộc chọn ngân hàng nhận")
        return self


class WithdrawalRead(ORMModel):
    id: int
    user_id: int
    amount: Decimal
    method: str
    bank_code: str | None
    bank_name: str | None
    account_name: str
    account_number: str
    status: str
    requested_at: datetime
    processed_at: datetime | None
    rejection_reason: str | None


class AffiliateWebhookOrder(BaseModel):
    platform: str
    platform_order_id: str
    tracking_id: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    order_amount: Decimal = Decimal("0")
    commission_amount: Decimal = Decimal("0")
    currency: str = "VND"
    order_status: str
    commission_status: str
    ordered_at: datetime | None = None
    completed_at: datetime | None = None


class AffiliateWebhookRequest(BaseModel):
    idempotency_key: str | None = None
    orders: list[AffiliateWebhookOrder]


class ZaloWebhookRequest(BaseModel):
    sender: dict
    message: dict | None = None
    event_name: str | None = None
    token: str | None = None