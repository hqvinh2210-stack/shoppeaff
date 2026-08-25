from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class AffiliateLinkRequest:
    original_url: str
    normalized_url: str
    tracking_id: str
    product_id: str | None = None
    shop_id: str | None = None


@dataclass(frozen=True)
class AffiliateLinkResult:
    affiliate_url: str
    platform: str


@dataclass(frozen=True)
class AffiliateOrderPayload:
    platform: str
    platform_order_id: str
    tracking_id: str | None
    product_id: str | None
    product_name: str | None
    order_amount: Decimal
    commission_amount: Decimal
    currency: str
    order_status: str
    commission_status: str
    ordered_at: datetime | None = None
    completed_at: datetime | None = None


class AffiliateProvider(ABC):
    @abstractmethod
    def generate_affiliate_link(self, request: AffiliateLinkRequest) -> AffiliateLinkResult:
        raise NotImplementedError

    @abstractmethod
    def get_orders(self) -> list[AffiliateOrderPayload]:
        raise NotImplementedError

    @abstractmethod
    def get_commissions(self) -> list[AffiliateOrderPayload]:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, platform_order_id: str) -> str:
        raise NotImplementedError