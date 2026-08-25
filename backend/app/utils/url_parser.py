import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


SHOPEE_HOST_PATTERN = re.compile(r"(^|\.)shopee\.vn$", re.IGNORECASE)
PRODUCT_PATH_PATTERN = re.compile(r"(?:i\.|product/)(?P<shop_id>\d+)[./](?P<product_id>\d+)")


@dataclass(frozen=True)
class ShopeeUrlInfo:
    original_url: str
    normalized_url: str
    product_id: str | None = None
    shop_id: str | None = None


def is_shopee_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(SHOPEE_HOST_PATTERN.search(parsed.netloc.lower()))


def find_shopee_url(text: str) -> str | None:
    for candidate in re.findall(r"https?://[^\s]+", text or ""):
        candidate = candidate.rstrip(".,!?)]}")
        if is_shopee_url(candidate):
            return candidate
    return None


def normalize_shopee_url(url: str) -> ShopeeUrlInfo:
    raw = url.strip()
    if not is_shopee_url(raw):
        raise ValueError("URL is not a supported Shopee Vietnam URL")

    parsed = urlparse(raw)
    query = parse_qs(parsed.query)
    allowed_query = {key: value for key, value in query.items() if key in {"sp_atk"}}
    normalized = urlunparse(
        (
            "https",
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            "",
            urlencode(allowed_query, doseq=True),
            "",
        )
    )

    product_id = None
    shop_id = None
    match = PRODUCT_PATH_PATTERN.search(parsed.path)
    if match:
        shop_id = match.group("shop_id")
        product_id = match.group("product_id")

    return ShopeeUrlInfo(original_url=raw, normalized_url=normalized, product_id=product_id, shop_id=shop_id)