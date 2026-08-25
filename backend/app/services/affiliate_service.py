from sqlalchemy.orm import Session

from app.models.entities import AffiliateLink
from app.providers.affiliate.base import AffiliateLinkRequest, AffiliateProvider
from app.utils.tracking import build_tracking_id
from app.utils.url_parser import normalize_shopee_url


class AffiliateService:
    def __init__(self, db: Session, provider: AffiliateProvider):
        self.db = db
        self.provider = provider

    def generate_link(self, user_id: int, original_url: str) -> AffiliateLink:
        url_info = normalize_shopee_url(original_url)

        link = AffiliateLink(
            user_id=user_id,
            original_url=url_info.original_url,
            normalized_url=url_info.normalized_url,
            product_id=url_info.product_id,
            shop_id=url_info.shop_id,
            tracking_id="PENDING",
            platform="PENDING",
        )
        self.db.add(link)
        self.db.flush()

        link.tracking_id = build_tracking_id(user_id=user_id, affiliate_link_id=link.id)
        result = self.provider.generate_affiliate_link(
            AffiliateLinkRequest(
                original_url=link.original_url,
                normalized_url=link.normalized_url,
                tracking_id=link.tracking_id,
                product_id=link.product_id,
                shop_id=link.shop_id,
            )
        )
        link.affiliate_url = result.affiliate_url.format(tracking_id=link.tracking_id)
        link.platform = result.platform
        self.db.flush()
        return link