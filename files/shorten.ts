import { customAlphabet } from "nanoid";
import { getSupabaseAdmin } from "./supabase";

// Bảng chữ giống ví dụ (chữ hoa/thường + số), bỏ ký tự dễ nhầm: 0/O, 1/l/I
const ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz";
const nanoid = customAlphabet(ALPHABET, 8);

// Chỉ cho phép rút gọn link trỏ tới các domain affiliate hợp lệ,
// tránh bị lợi dụng làm open-redirect cho domain bất kỳ.
const ALLOWED_TARGET_HOSTS = [
  "s.shopee.vn",
  "shopee.vn",
  "vn.shp.ee",
];

export function isAllowedTargetUrl(targetUrl: string): boolean {
  try {
    const u = new URL(targetUrl);
    return ALLOWED_TARGET_HOSTS.some(
      (host) => u.hostname === host || u.hostname.endsWith(`.${host}`),
    );
  } catch {
    return false;
  }
}

export interface CreateShortLinkInput {
  targetUrl: string;
  itemId?: string | null;
  source?: string | null; // "telegram" | "zalo" | "web" | ...
  meta?: Record<string, unknown> | null; // vd: commission info để hiển thị lại sau này
}

export interface ShortLinkRecord {
  code: string;
  target_url: string;
  item_id: string | null;
  source: string | null;
  meta: Record<string, unknown> | null;
  click_count: number;
  created_at: string;
}

/**
 * Tạo short link mới. Nếu itemId + source đã có link rút gọn trước đó thì
 * trả lại link cũ luôn (tránh sinh trùng nhiều mã cho cùng 1 sản phẩm/kênh).
 */
export async function createShortLink(
  input: CreateShortLinkInput,
): Promise<ShortLinkRecord> {
  if (!isAllowedTargetUrl(input.targetUrl)) {
    throw new Error("targetUrl không thuộc domain affiliate được phép");
  }

  const supabase = getSupabaseAdmin();

  if (input.itemId && input.source) {
    const { data: existing } = await supabase
      .from("short_links")
      .select("*")
      .eq("item_id", input.itemId)
      .eq("source", input.source)
      .eq("target_url", input.targetUrl)
      .maybeSingle();

    if (existing) return existing as ShortLinkRecord;
  }

  // Thử tối đa 5 lần nếu đụng trùng mã (rất hiếm với 8 ký tự bảng 57 ký tự)
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = nanoid();
    const { data, error } = await supabase
      .from("short_links")
      .insert({
        code,
        target_url: input.targetUrl,
        item_id: input.itemId ?? null,
        source: input.source ?? null,
        meta: input.meta ?? null,
      })
      .select("*")
      .single();

    if (!error) return data as ShortLinkRecord;
    if (error.code !== "23505") throw error; // không phải lỗi trùng khoá -> ném lỗi luôn
  }

  throw new Error("Không tạo được mã ngắn sau nhiều lần thử");
}

export async function resolveShortLink(
  code: string,
): Promise<ShortLinkRecord | null> {
  const supabase = getSupabaseAdmin();
  const { data } = await supabase
    .from("short_links")
    .select("*")
    .eq("code", code)
    .maybeSingle();
  return (data as ShortLinkRecord) ?? null;
}

export async function logClick(
  code: string,
  info: { ip?: string | null; userAgent?: string | null; referer?: string | null },
): Promise<void> {
  const supabase = getSupabaseAdmin();
  // Fire-and-forget về mặt logic nghiệp vụ, nhưng vẫn await để chạy trong edge runtime
  // (một số runtime sẽ kill request sau khi response được trả, nên không thể "quên" nó).
  await Promise.all([
    supabase.from("short_link_clicks").insert({
      code,
      ip: info.ip ?? null,
      user_agent: info.userAgent ?? null,
      referer: info.referer ?? null,
    }),
    supabase.rpc("increment_click_count", { p_code: code }),
  ]);
}
