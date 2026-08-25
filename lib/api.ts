/**
 * Một điểm gọi API duy nhất cho toàn bộ frontend.
 *
 * Trước đây trang chủ và `auth-form` tự viết `fetch` riêng nên luật xử lý token
 * và lỗi bị lệch nhau. Mọi màn hình giờ đi qua `apiFetch`, tuân theo đúng quy
 * ước trong `docs/01-ROLE-TINH-NANG-RANG-BUOC-FE-BE.md` mục 4.1–4.2.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const TOKEN_KEY = "cashback_access_token";
export const REFRESH_KEY = "cashback_refresh_token";

export type TokenPair = { access_token: string; refresh_token: string };

export function readToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

export function readRefreshToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(REFRESH_KEY) ?? "";
}

export function writeToken(token: string, refreshToken?: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/**
 * Đổi refresh token lấy cặp token mới.
 *
 * Access token chỉ sống 30 phút. Không có bước này thì người dùng bị đá ra
 * giữa thao tác — ví dụ đang điền form rút tiền thì mất phiên.
 */
export async function refreshSession(): Promise<TokenPair | null> {
  const refreshToken = readRefreshToken();
  if (!refreshToken) return null;
  try {
    const pair = await apiFetch<TokenPair>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
    writeToken(pair.access_token, pair.refresh_token);
    return pair;
  } catch {
    // Refresh token cũng hết hạn hoặc tài khoản bị khoá — hết đường cứu phiên.
    return null;
  }
}

/** Lỗi mang theo HTTP status để nơi gọi phân biệt được 401 với 400/403. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }

  /** Token thiếu, sai hoặc hết hạn — nơi gọi phải xoá phiên. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** Đăng nhập rồi nhưng không đủ quyền — giữ nguyên phiên. */
  get isForbidden(): boolean {
    return this.status === 403;
  }
}

type ApiOptions = Omit<RequestInit, "body"> & {
  token?: string;
  body?: unknown;
};

export async function apiFetch<T = unknown>(
  path: string,
  { token, body, headers, ...init }: ApiOptions = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });

  // 204 No Content (ví dụ DELETE /zalo/unlink) không có thân phản hồi để parse.
  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(response.status, readDetail(data));
  }
  return data as T;
}

/**
 * FastAPI trả `detail` ở hai dạng: chuỗi (HTTPException do mình raise) hoặc
 * mảng lỗi của Pydantic khi 422. Bỏ qua dạng mảng sẽ khiến người dùng thấy
 * "Không thể kết nối máy chủ" cho một lỗi nhập liệu — nên đọc cả hai.
 */
function readDetail(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item as { msg?: unknown })?.msg)
      .filter((msg): msg is string => typeof msg === "string")
      // Pydantic gắn tiền tố "Value error, " vào thông điệp của validator.
      .map((msg) => msg.replace(/^Value error,\s*/, ""));
    if (messages.length) return messages.join(" · ");
  }
  return "Không thể kết nối máy chủ";
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
