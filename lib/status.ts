/**
 * Nguồn sự thật duy nhất cho các giá trị trạng thái mà backend trả về.
 *
 * File này PHẢI khớp tuyệt đối với `backend/app/models/enums.py`.
 * Khi backend thêm/bớt một giá trị enum, sửa ở đây trước rồi mới sửa UI —
 * tuyệt đối không tự chế giá trị trạng thái ở trong component.
 *
 * Backend luôn trả mã tiếng Anh; nhãn tiếng Việt chỉ dùng để hiển thị.
 */

/** Mức độ hiển thị, dùng để chọn màu badge thống nhất trên toàn bộ UI. */
export type StatusTone = "neutral" | "waiting" | "success" | "danger";

type StatusMeta = { label: string; tone: StatusTone };

/* -------------------------------------------------------------------------- */
/* UserStatus                                                                  */
/* -------------------------------------------------------------------------- */

export const USER_STATUSES = ["ACTIVE", "INACTIVE", "BLOCKED"] as const;
export type UserStatus = (typeof USER_STATUSES)[number];

export const USER_STATUS_META: Record<UserStatus, StatusMeta> = {
  ACTIVE: { label: "Đang hoạt động", tone: "success" },
  INACTIVE: { label: "Ngừng hoạt động", tone: "neutral" },
  BLOCKED: { label: "Bị khoá", tone: "danger" },
};

/* -------------------------------------------------------------------------- */
/* LinkStatus                                                                  */
/* -------------------------------------------------------------------------- */

export const LINK_STATUSES = ["ACTIVE", "INACTIVE", "EXPIRED", "USED"] as const;
export type LinkStatus = (typeof LINK_STATUSES)[number];

export const LINK_STATUS_META: Record<LinkStatus, StatusMeta> = {
  ACTIVE: { label: "Đang hiệu lực", tone: "success" },
  INACTIVE: { label: "Đã ngắt", tone: "neutral" },
  EXPIRED: { label: "Đã hết hạn", tone: "danger" },
  USED: { label: "Đã sử dụng", tone: "neutral" },
};

/* -------------------------------------------------------------------------- */
/* OrderStatus                                                                 */
/* -------------------------------------------------------------------------- */

export const ORDER_STATUSES = [
  "PENDING",
  "CONFIRMED",
  "COMPLETED",
  "CANCELLED",
  "REVERSED",
  "ATTRIBUTION_REVIEW",
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const ORDER_STATUS_META: Record<OrderStatus, StatusMeta> = {
  PENDING: { label: "Đang chờ", tone: "waiting" },
  CONFIRMED: { label: "Đã xác nhận", tone: "success" },
  COMPLETED: { label: "Hoàn tất", tone: "success" },
  CANCELLED: { label: "Đã huỷ", tone: "danger" },
  REVERSED: { label: "Đã thu hồi", tone: "danger" },
  ATTRIBUTION_REVIEW: { label: "Chờ quy gán", tone: "waiting" },
};

/* -------------------------------------------------------------------------- */
/* CommissionStatus                                                            */
/* -------------------------------------------------------------------------- */

export const COMMISSION_STATUSES = [
  "PENDING",
  "CONFIRMED",
  "SETTLED",
  "REJECTED",
  "REVERSED",
] as const;
export type CommissionStatus = (typeof COMMISSION_STATUSES)[number];

export const COMMISSION_STATUS_META: Record<CommissionStatus, StatusMeta> = {
  PENDING: { label: "Đang chờ", tone: "waiting" },
  CONFIRMED: { label: "Đã xác nhận", tone: "success" },
  SETTLED: { label: "Đã đối soát", tone: "success" },
  REJECTED: { label: "Bị từ chối", tone: "danger" },
  REVERSED: { label: "Đã thu hồi", tone: "danger" },
};

/* -------------------------------------------------------------------------- */
/* CashbackStatus                                                              */
/* -------------------------------------------------------------------------- */

export const CASHBACK_STATUSES = [
  "NONE",
  "PENDING",
  "APPROVED",
  "REVERSED",
  "REVIEW",
] as const;
export type CashbackStatus = (typeof CASHBACK_STATUSES)[number];

export const CASHBACK_STATUS_META: Record<CashbackStatus, StatusMeta> = {
  NONE: { label: "Chưa ghi nhận", tone: "neutral" },
  PENDING: { label: "Chờ duyệt", tone: "waiting" },
  APPROVED: { label: "Đã duyệt", tone: "success" },
  REVERSED: { label: "Đã thu hồi", tone: "danger" },
  REVIEW: { label: "Chờ đối soát", tone: "waiting" },
};

/** Bộ lọc đơn hàng trên dashboard: "ALL" + đúng tập giá trị của backend. */
export const CASHBACK_FILTERS = ["ALL", ...CASHBACK_STATUSES] as const;
export type CashbackFilter = (typeof CASHBACK_FILTERS)[number];

export const CASHBACK_FILTER_LABELS: Record<CashbackFilter, string> = {
  ALL: "Tất cả",
  NONE: CASHBACK_STATUS_META.NONE.label,
  PENDING: CASHBACK_STATUS_META.PENDING.label,
  APPROVED: CASHBACK_STATUS_META.APPROVED.label,
  REVERSED: CASHBACK_STATUS_META.REVERSED.label,
  REVIEW: CASHBACK_STATUS_META.REVIEW.label,
};

/* -------------------------------------------------------------------------- */
/* TransactionType / TransactionStatus                                         */
/* -------------------------------------------------------------------------- */

export const TRANSACTION_TYPES = [
  "CASHBACK_PENDING",
  "CASHBACK_APPROVED",
  "CASHBACK_REVERSED",
  "WITHDRAWAL",
  "WITHDRAWAL_REJECTED",
  "ADJUSTMENT",
] as const;
export type TransactionType = (typeof TRANSACTION_TYPES)[number];

export const TRANSACTION_TYPE_META: Record<TransactionType, StatusMeta> = {
  CASHBACK_PENDING: { label: "Hoàn tiền chờ duyệt", tone: "waiting" },
  CASHBACK_APPROVED: { label: "Hoàn tiền đã duyệt", tone: "success" },
  CASHBACK_REVERSED: { label: "Hoàn tiền bị thu hồi", tone: "danger" },
  WITHDRAWAL: { label: "Rút tiền", tone: "neutral" },
  WITHDRAWAL_REJECTED: { label: "Hoàn lại do từ chối rút", tone: "waiting" },
  ADJUSTMENT: { label: "Điều chỉnh thủ công", tone: "neutral" },
};

export const TRANSACTION_STATUSES = [
  "PENDING",
  "COMPLETED",
  "REVERSED",
  "REJECTED",
] as const;
export type TransactionStatus = (typeof TRANSACTION_STATUSES)[number];

export const TRANSACTION_STATUS_META: Record<TransactionStatus, StatusMeta> = {
  PENDING: { label: "Đang chờ", tone: "waiting" },
  COMPLETED: { label: "Hoàn tất", tone: "success" },
  REVERSED: { label: "Đã thu hồi", tone: "danger" },
  REJECTED: { label: "Bị từ chối", tone: "danger" },
};

/* -------------------------------------------------------------------------- */
/* WithdrawalStatus                                                            */
/* -------------------------------------------------------------------------- */

export const WITHDRAWAL_STATUSES = [
  "PENDING",
  "PROCESSING",
  "COMPLETED",
  "REJECTED",
] as const;
export type WithdrawalStatus = (typeof WITHDRAWAL_STATUSES)[number];

export const WITHDRAWAL_STATUS_META: Record<WithdrawalStatus, StatusMeta> = {
  PENDING: { label: "Chờ xử lý", tone: "waiting" },
  PROCESSING: { label: "Đang chi trả", tone: "waiting" },
  COMPLETED: { label: "Đã chi trả", tone: "success" },
  REJECTED: { label: "Bị từ chối", tone: "danger" },
};

/** Phương thức rút tiền được backend chấp nhận (thay cho việc hardcode "BANK"). */
export const WITHDRAWAL_METHODS = [
  { value: "BANK", label: "Chuyển khoản ngân hàng" },
  { value: "MOMO", label: "Ví MoMo" },
] as const;
export type WithdrawalMethod = (typeof WITHDRAWAL_METHODS)[number]["value"];

/* -------------------------------------------------------------------------- */
/* Tiện ích tra cứu                                                            */
/* -------------------------------------------------------------------------- */

/**
 * Tra nhãn tiếng Việt cho một mã trạng thái.
 *
 * Nếu backend trả về một mã chưa có trong bảng (ví dụ enum mới được thêm mà FE
 * chưa cập nhật) thì trả lại đúng mã gốc thay vì hiển thị rỗng — để lỗi lệch
 * hợp đồng lộ ra ngay trên UI thay vì bị nuốt mất.
 */
export function statusLabel(
  meta: Record<string, StatusMeta>,
  code: string,
): string {
  return meta[code]?.label ?? code;
}

export function statusTone(
  meta: Record<string, StatusMeta>,
  code: string,
): StatusTone {
  return meta[code]?.tone ?? "neutral";
}

/** Màu badge dùng chung cho mọi trạng thái, chọn theo tone. */
export const TONE_COLORS: Record<StatusTone, { color: string; background: string }> = {
  neutral: { color: "#687386", background: "#f1f3f7" },
  waiting: { color: "#ba8500", background: "#fff6d9" },
  success: { color: "#159366", background: "#e4f7ed" },
  danger: { color: "#c45142", background: "#fff0ed" },
};
