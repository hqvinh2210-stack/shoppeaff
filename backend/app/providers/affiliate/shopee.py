from app.models.enums import AffiliatePlatform
from app.providers.affiliate.base import AffiliateLinkRequest, AffiliateLinkResult, AffiliateOrderPayload, AffiliateProvider


class ShopeeAffiliateProvider(AffiliateProvider):
    """
    Shopee adapter boundary.

    This class intentionally does not invent Shopee Affiliate API fields.
    Replace this implementation only after inspecting official Shopee Affiliate
    documentation for link generation, sub_id/tracking support, order fields,
    commission fields, statuses, settlement fields, and attribution fields.
    """

    def generate_affiliate_link(self, request: AffiliateLinkRequest) -> AffiliateLinkResult:
        raise NotImplementedError(
            "Shopee Affiliate API documentation is required before implementing real link generation."
        )

    def get_orders(self) -> list[AffiliateOrderPayload]:
        raise NotImplementedError("Shopee Affiliate order API documentation is required before implementation.")

    def get_commissions(self) -> list[AffiliateOrderPayload]:
        raise NotImplementedError("Shopee Affiliate commission API documentation is required before implementation.")

    def get_order_status(self, platform_order_id: str) -> str:
        raise NotImplementedError("Shopee Affiliate order status API documentation is required before implementation.")


class MockAffiliateProvider(AffiliateProvider):
    def generate_affiliate_link(self, request: AffiliateLinkRequest) -> AffiliateLinkResult:
        return AffiliateLinkResult(
            affiliate_url=f"https://mock-affiliate.local/redirect?tracking_id={request.tracking_id}&url={request.normalized_url}",
            platform=AffiliatePlatform.MOCK.value,
        )

    def get_orders(self) -> list[AffiliateOrderPayload]:
        return []

    def get_commissions(self) -> list[AffiliateOrderPayload]:
        return []

    def get_order_status(self, platform_order_id: str) -> str:
        return "UNKNOWN"