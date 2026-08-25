"""
shopee_link_handler.py
=======================
Handler cho bot Telegram (python-telegram-bot v21): nhận diện link Shopee
trong tin nhắn, gọi API data.addlivetag.com để lấy thông tin sản phẩm +
hoa hồng, sinh link affiliate chuẩn (an_redir), và trả lời trong chat.

Cách gắn vào bot hiện tại (bot.py của bạn):

    from shopee_link_handler import handle_shopee_link, SHOPEE_LINK_REGEX
    from telegram.ext import MessageHandler, filters

    application.add_handler(
        MessageHandler(filters.Regex(SHOPEE_LINK_REGEX), handle_shopee_link)
    )

Biến môi trường cần set:
    SHOPEE_AFFILIATE_ID   - affiliate_id của bạn (bắt buộc để sinh link affiliate thật)
    SHOPEE_BASE_RATE      - (tuỳ chọn) % hoa hồng sàn cơ bản tài khoản bạn, vd "8"
    SHOPEE_CAP            - (tuỳ chọn) trần hoa hồng sàn VNĐ, vd "20000"
    SHOPEE_SUBID_PUBLISHER- (tuỳ chọn) tên publisher cho sub_id, mặc định "tgbot"
"""

import os
import re
import logging
from urllib.parse import quote
from typing import Optional

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cấu hình
# ---------------------------------------------------------------------------
API_BASE = "https://data.addlivetag.com"
PRODUCT_DATA_ENDPOINT = f"{API_BASE}/product-data/product-data.php"

AFFILIATE_ID = os.getenv("SHOPEE_AFFILIATE_ID", "")
BASE_RATE = os.getenv("SHOPEE_BASE_RATE")  # vd "8" -> 8%
CAP = os.getenv("SHOPEE_CAP")              # vd "20000"
SUBID_PUBLISHER = os.getenv("SHOPEE_SUBID_PUBLISHER", "tgbot")

# Dịch vụ rút gọn link riêng (giatotday.vn) - tuỳ chọn, nếu không cấu hình
# thì bot vẫn gửi link affiliate dạng dài (an_redir) như bình thường.
SHORTENER_BASE_URL = os.getenv("SHORTENER_PUBLIC_BASE_URL")  # vd https://giatotday.vn
SHORTENER_API_KEY = os.getenv("SHORTENER_API_KEY")

REQUEST_TIMEOUT = 10.0

# Regex nhận diện link Shopee trong tin nhắn (đủ dạng: full, slug, rút gọn)
SHOPEE_LINK_REGEX = re.compile(
    r"https?://(?:s\.shopee\.vn|vn\.shp\.ee|shopee\.vn)\S+",
    re.IGNORECASE,
)

# Regex bóc tách item_id từ link "sạch" (không cần gọi resolve)
_FULL_PRODUCT_RE = re.compile(r"shopee\.vn/product/(\d+)/(\d+)")
_SLUG_RE = re.compile(r"shopee\.vn/[^\s?]+-i\.(\d+)\.(\d+)")


# ---------------------------------------------------------------------------
# Bóc tách item_id / chuẩn bị tham số gọi API
# ---------------------------------------------------------------------------
def extract_item_id(url: str) -> Optional[str]:
    """Trả về item_id nếu bóc được trực tiếp từ URL (link full/slug, KHÔNG cần resolve)."""
    m = _FULL_PRODUCT_RE.search(url)
    if m:
        return m.group(2)
    m = _SLUG_RE.search(url)
    if m:
        return m.group(2)
    return None  # link rút gọn (s.shopee.vn / vn.shp.ee) -> để API tự resolve qua param url


# ---------------------------------------------------------------------------
# Gọi API product-data
# ---------------------------------------------------------------------------
async def fetch_product_data(url: str) -> dict:
    """Gọi API product-data.php, ưu tiên item_id (nhanh) nếu bóc được, fallback dùng url."""
    item_id = extract_item_id(url)
    params: dict = {}
    if item_id:
        params["item_id"] = item_id
    else:
        params["url"] = url  # link rút gọn, API tự resolve (chậm hơn, ~30 req/phút)

    if BASE_RATE:
        params["base_rate"] = BASE_RATE
    if CAP:
        params["cap"] = CAP

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(PRODUCT_DATA_ENDPOINT, params=params)

    if resp.status_code == 429:
        return {"status": "error", "message": "Rate limit exceeded"}

    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Sinh link affiliate (an_redir)
# ---------------------------------------------------------------------------
def build_affiliate_link(
    landing_link: str,
    item_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[str]:
    """Sinh link affiliate chuẩn 2026 dạng an_redir. Trả None nếu chưa cấu hình affiliate_id."""
    if not AFFILIATE_ID:
        return None

    encoded_landing = quote(landing_link, safe="")
    sub_parts = [
        SUBID_PUBLISHER,
        "telegram",
        item_id or "unknown",
        str(user_id or "0"),
        "",  # note - để trống, có thể tuỳ biến
    ]
    sub_id = "-".join(sub_parts)

    return (
        f"https://s.shopee.vn/an_redir"
        f"?origin_link={encoded_landing}"
        f"&affiliate_id={AFFILIATE_ID}"
        f"&sub_id={sub_id}"
    )


async def shorten_link(aff_link: str, item_id: Optional[str]) -> str:
    """Gọi giatotday.vn/api/shorten để rút gọn link affiliate.
    Nếu chưa cấu hình hoặc gọi lỗi -> trả lại nguyên link dài (an_redir), không chặn bot."""
    if not SHORTENER_BASE_URL or not SHORTENER_API_KEY:
        return aff_link

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{SHORTENER_BASE_URL}/api/shorten",
                headers={"X-API-Key": SHORTENER_API_KEY},
                json={"targetUrl": aff_link, "itemId": item_id, "source": "telegram"},
            )
        data = resp.json()
        if data.get("status") == "success" and data.get("shortUrl"):
            return data["shortUrl"]
    except httpx.HTTPError as e:
        logger.warning("Loi goi shortener, dung link dai: %s", e)

    return aff_link


# ---------------------------------------------------------------------------
# Format tin nhắn trả lời
# ---------------------------------------------------------------------------
def _fmt_vnd(v) -> str:
    try:
        return f"{float(v):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return str(v)


def format_product_message(info: dict, warning: Optional[str] = None) -> str:
    name = info.get("productName", "N/A")
    shop = info.get("shopName", "N/A")
    price = _fmt_vnd(info.get("price"))
    sales = info.get("sales", 0)
    rating = info.get("rating", "N/A")

    total_pct = info.get("totalRatePercent", 0)
    commission = _fmt_vnd(info.get("commission"))
    seller_pct = info.get("sellerRatePercent", 0)
    seller_com = _fmt_vnd(info.get("sellerComFinal"))
    shopee_pct = info.get("shopeeRatePercent", 0)
    shopee_com = _fmt_vnd(info.get("shopeeComFinal"))
    is_xtra = info.get("isXtra")
    is_capped = info.get("isCapped")

    lines = [
        f"📦 <b>{name}</b>",
        f"🏪 {shop}",
        f"💰 Giá: {price}đ  |  ⭐ {rating}  |  Đã bán: {sales}",
        "",
        f"🎯 Tổng hoa hồng: <b>{total_pct}%</b> (~{commission}đ)",
        f"   • Sàn: {shopee_pct}% (~{shopee_com}đ)" + (" [đã cap]" if is_capped else ""),
        f"   • Seller{' 🔥Xtra' if is_xtra else ''}: {seller_pct}% (~{seller_com}đ)",
    ]

    if warning:
        lines.append(f"\n⚠️ {warning}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Telegram handler
# ---------------------------------------------------------------------------
async def handle_shopee_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    match = SHOPEE_LINK_REGEX.search(text)
    if not match:
        return

    url = match.group(0)
    user_id = update.effective_user.id if update.effective_user else None

    processing_msg = await update.message.reply_text("🔎 Đang tra cứu sản phẩm...")

    try:
        data = await fetch_product_data(url)
    except httpx.HTTPError as e:
        logger.warning("Loi goi API product-data: %s", e)
        await processing_msg.edit_text("❌ Không gọi được API, thử lại sau.")
        return

    if data.get("status") != "success":
        msg = data.get("message", "Không lấy được dữ liệu sản phẩm.")
        await processing_msg.edit_text(f"❌ {msg}")
        return

    info = data.get("productInfo", {})
    warning = data.get("warning")
    item_id = info.get("itemId") or extract_item_id(url)
    landing_link = info.get("productLink") or url

    aff_link = build_affiliate_link(landing_link, item_id=item_id, user_id=user_id)
    if aff_link:
        aff_link = await shorten_link(aff_link, item_id)

    caption = format_product_message(info, warning=warning)

    keyboard = None
    if aff_link:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔗 Lấy link affiliate", url=aff_link)]]
        )
    else:
        caption += "\n\n⚠️ Chưa cấu hình SHOPEE_AFFILIATE_ID nên chưa sinh được link affiliate."

    image_url = info.get("imageUrl")
    await processing_msg.delete()

    if image_url:
        await update.message.reply_photo(
            photo=image_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
