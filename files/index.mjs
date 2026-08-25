/**
 * index.mjs - Bot Zalo cá nhân (dùng zca-js, KHÔNG chính thức)
 * ---------------------------------------------------------------
 * Đăng nhập qua QR vào 1 tài khoản Zalo cá nhân, lắng nghe tin nhắn
 * (chat riêng + nhóm bạn bè), khi có link Shopee thì tra cứu thông
 * tin sản phẩm + hoa hồng qua data.addlivetag.com và trả lời kèm
 * link affiliate.
 *
 * LƯU Ý QUAN TRỌNG:
 * - zca-js là thư viện KHÔNG chính thức (giả lập Zalo Web), dùng sai
 *   quy định điều khoản Zalo có thể khiến tài khoản bị khoá/hạn chế.
 *   Nên test với 1 tài khoản phụ trước, tránh spam / tần suất cao.
 * - Chỉ 1 phiên listener chạy được cùng lúc cho 1 tài khoản; nếu mở
 *   Zalo Web song song thì listener của bot sẽ bị dừng.
 *
 * Cài đặt:
 *   npm install zca-js
 *
 * Chạy:
 *   SHOPEE_AFFILIATE_ID=xxxx node index.mjs
 *   -> quét QR bằng app Zalo trên điện thoại tài khoản muốn dùng làm bot
 *
 * Biến môi trường:
 *   SHOPEE_AFFILIATE_ID    - bắt buộc để sinh link affiliate thật
 *   SHOPEE_BASE_RATE       - tuỳ chọn, % hoa hồng sàn cơ bản (vd "8")
 *   SHOPEE_CAP             - tuỳ chọn, trần hoa hồng sàn VNĐ (vd "20000")
 *   SHOPEE_SUBID_PUBLISHER - tuỳ chọn, tên publisher cho sub_id, mặc định "zalobot"
 *   ZALO_ONLY_GROUPS       - tuỳ chọn, "1" để bot chỉ trả lời trong nhóm (bỏ qua chat riêng)
 */

import { Zalo, ThreadType } from "zca-js";

// ---------------------------------------------------------------------------
// Cấu hình
// ---------------------------------------------------------------------------
const API_BASE = "https://data.addlivetag.com";
const PRODUCT_DATA_ENDPOINT = `${API_BASE}/product-data/product-data.php`;

const AFFILIATE_ID = process.env.SHOPEE_AFFILIATE_ID || "";
const BASE_RATE = process.env.SHOPEE_BASE_RATE;
const CAP = process.env.SHOPEE_CAP;
const SUBID_PUBLISHER = process.env.SHOPEE_SUBID_PUBLISHER || "zalobot";
const ONLY_GROUPS = process.env.ZALO_ONLY_GROUPS === "1";

// Dịch vụ rút gọn link riêng (giatotday.vn) - tuỳ chọn.
const SHORTENER_BASE_URL = process.env.SHORTENER_PUBLIC_BASE_URL; // vd https://giatotday.vn
const SHORTENER_API_KEY = process.env.SHORTENER_API_KEY;

const REQUEST_TIMEOUT_MS = 10_000;

// Regex nhận diện link Shopee trong tin nhắn
const SHOPEE_LINK_REGEX = /https?:\/\/(?:s\.shopee\.vn|vn\.shp\.ee|shopee\.vn)\S+/i;

// Regex bóc item_id trực tiếp từ link "sạch" (không cần API resolve)
const FULL_PRODUCT_RE = /shopee\.vn\/product\/(\d+)\/(\d+)/;
const SLUG_RE = /shopee\.vn\/[^\s?]+-i\.(\d+)\.(\d+)/;

// ---------------------------------------------------------------------------
// Helpers: item_id / gọi API / affiliate link / format
// ---------------------------------------------------------------------------
function extractItemId(url) {
  let m = FULL_PRODUCT_RE.exec(url);
  if (m) return m[2];
  m = SLUG_RE.exec(url);
  if (m) return m[2];
  return null; // link rút gọn -> để API tự resolve qua param url
}

async function fetchProductData(url) {
  const itemId = extractItemId(url);
  const params = new URLSearchParams();
  if (itemId) {
    params.set("item_id", itemId);
  } else {
    params.set("url", url); // link rút gọn, API tự resolve (~30 req/phút)
  }
  if (BASE_RATE) params.set("base_rate", BASE_RATE);
  if (CAP) params.set("cap", CAP);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${PRODUCT_DATA_ENDPOINT}?${params.toString()}`, {
      signal: controller.signal,
    });
    if (res.status === 429) {
      return { status: "error", message: "Rate limit exceeded" };
    }
    return await res.json();
  } finally {
    clearTimeout(timeout);
  }
}

function buildAffiliateLink(landingLink, itemId, userId) {
  if (!AFFILIATE_ID) return null;

  const encodedLanding = encodeURIComponent(landingLink);
  const subParts = [
    SUBID_PUBLISHER,
    "zalo",
    itemId || "unknown",
    String(userId || "0"),
    "",
  ];
  const subId = subParts.join("-");

  return `https://s.shopee.vn/an_redir?origin_link=${encodedLanding}&affiliate_id=${AFFILIATE_ID}&sub_id=${subId}`;
}

async function shortenLink(affLink, itemId) {
  // Nếu chưa cấu hình -> trả lại nguyên link dài (an_redir), không chặn bot.
  if (!SHORTENER_BASE_URL || !SHORTENER_API_KEY) return affLink;

  try {
    const res = await fetch(`${SHORTENER_BASE_URL}/api/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": SHORTENER_API_KEY },
      body: JSON.stringify({ targetUrl: affLink, itemId, source: "zalo" }),
    });
    const data = await res.json();
    if (data.status === "success" && data.shortUrl) return data.shortUrl;
  } catch (err) {
    console.warn("Loi goi shortener, dung link dai:", err.message);
  }

  return affLink;
}

function fmtVnd(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("vi-VN");
}

function formatProductMessage(info, warning) {
  const name = info.productName ?? "N/A";
  const shop = info.shopName ?? "N/A";
  const price = fmtVnd(info.price);
  const sales = info.sales ?? 0;
  const rating = info.rating ?? "N/A";

  const totalPct = info.totalRatePercent ?? 0;
  const commission = fmtVnd(info.commission);
  const sellerPct = info.sellerRatePercent ?? 0;
  const sellerCom = fmtVnd(info.sellerComFinal);
  const shopeePct = info.shopeeRatePercent ?? 0;
  const shopeeCom = fmtVnd(info.shopeeComFinal);
  const isXtra = info.isXtra;
  const isCapped = info.isCapped;

  const lines = [
    `📦 ${name}`,
    `🏪 ${shop}`,
    `💰 Giá: ${price}đ | ⭐ ${rating} | Đã bán: ${sales}`,
    "",
    `🎯 Tổng hoa hồng: ${totalPct}% (~${commission}đ)`,
    `   • Sàn: ${shopeePct}% (~${shopeeCom}đ)${isCapped ? " [đã cap]" : ""}`,
    `   • Seller${isXtra ? " 🔥Xtra" : ""}: ${sellerPct}% (~${sellerCom}đ)`,
  ];

  if (warning) lines.push(`\n⚠️ ${warning}`);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Xử lý 1 tin nhắn có chứa link Shopee
// ---------------------------------------------------------------------------
async function handleShopeeLink(api, message, url) {
  const threadId = message.threadId;
  const threadType = message.type; // ThreadType.User | ThreadType.Group
  const senderId = message.data?.uidFrom;

  let data;
  try {
    data = await fetchProductData(url);
  } catch (err) {
    console.error("Loi goi API product-data:", err.message);
    await api.sendMessage({ msg: "❌ Không gọi được API, thử lại sau." }, threadId, threadType);
    return;
  }

  if (data.status !== "success") {
    const msg = data.message || "Không lấy được dữ liệu sản phẩm.";
    await api.sendMessage({ msg: `❌ ${msg}` }, threadId, threadType);
    return;
  }

  const info = data.productInfo || {};
  const itemId = info.itemId || extractItemId(url);
  const landingLink = info.productLink || url;

  let affLink = buildAffiliateLink(landingLink, itemId, senderId);
  if (affLink) affLink = await shortenLink(affLink, itemId);

  let text = formatProductMessage(info, data.warning);
  text += affLink
    ? `\n\n🔗 Link affiliate:\n${affLink}`
    : "\n\n⚠️ Chưa cấu hình SHOPEE_AFFILIATE_ID nên chưa sinh được link affiliate.";

  await api.sendMessage(
    { msg: text, quote: message.data },
    threadId,
    threadType,
  );
}

// ---------------------------------------------------------------------------
// Khởi động bot
// ---------------------------------------------------------------------------
async function main() {
  const zalo = new Zalo();
  const api = await zalo.loginQR();

  console.log("Đăng nhập thành công. Bot đang lắng nghe tin nhắn...");

  api.listener.on("message", async (message) => {
    const isPlainText = typeof message.data?.content === "string";
    if (message.isSelf || !isPlainText) return;
    if (ONLY_GROUPS && message.type !== ThreadType.Group) return;

    const match = SHOPEE_LINK_REGEX.exec(message.data.content);
    if (!match) return;

    try {
      await handleShopeeLink(api, message, match[0]);
    } catch (err) {
      console.error("Loi xu ly link Shopee:", err);
    }
  });

  api.listener.start();
}

main().catch((err) => {
  console.error("Bot khoi dong that bai:", err);
  process.exit(1);
});
