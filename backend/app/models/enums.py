from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class LinkStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"
    USED = "USED"


class AffiliatePlatform(StrEnum):
    SHOPEE = "SHOPEE"
    MOCK = "MOCK"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REVERSED = "REVERSED"
    ATTRIBUTION_REVIEW = "ATTRIBUTION_REVIEW"


class CommissionStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    REVERSED = "REVERSED"


class CashbackStatus(StrEnum):
    NONE = "NONE"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REVERSED = "REVERSED"
    REVIEW = "REVIEW"


class TransactionType(StrEnum):
    CASHBACK_PENDING = "CASHBACK_PENDING"
    CASHBACK_APPROVED = "CASHBACK_APPROVED"
    CASHBACK_REVERSED = "CASHBACK_REVERSED"
    WITHDRAWAL = "WITHDRAWAL"
    WITHDRAWAL_REJECTED = "WITHDRAWAL_REJECTED"
    ADJUSTMENT = "ADJUSTMENT"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVERSED = "REVERSED"
    REJECTED = "REJECTED"


class WithdrawalMethod(StrEnum):
    BANK = "BANK"
    MOMO = "MOMO"


class WithdrawalStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"