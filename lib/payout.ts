/**
 * Danh mục phương thức nhận tiền và ngân hàng.
 *
 * `WITHDRAWAL_METHODS` trong `lib/status.ts` phản chiếu enum `WithdrawalMethod`
 * của backend; file này bổ sung phần chỉ giao diện cần (nhãn ô nhập, danh sách
 * ngân hàng, quy tắc kiểm tra số tài khoản).
 */
import { WITHDRAWAL_METHODS, type WithdrawalMethod } from "./status";

const methodName = (value: WithdrawalMethod) =>
  WITHDRAWAL_METHODS.find((item) => item.value === value)?.label ?? value;

export const MIN_WITHDRAWAL = 30_000;

/** Phí rút hiện tại. Đổi ở đây nếu về sau có thu phí. */
export const WITHDRAWAL_FEE = 0;

export type PayoutMethod = WithdrawalMethod;

type MethodSpec = {
  value: PayoutMethod;
  /** Nhãn lấy từ `lib/status.ts` để không lệch với enum backend. */
  label: string;
  hint: string;
  /** Ví điện tử không cần chọn ngân hàng. */
  needsBank: boolean;
  accountLabel: string;
  accountPlaceholder: string;
  /** Độ dài hợp lệ của số tài khoản / số điện thoại. */
  accountMin: number;
  accountMax: number;
};

export const PAYOUT_METHODS: MethodSpec[] = [
  {
    value: "BANK",
    label: methodName("BANK"),
    hint: "Tiền về tài khoản ngân hàng trong 1–24 giờ làm việc.",
    needsBank: true,
    accountLabel: "Số tài khoản ngân hàng",
    accountPlaceholder: "Nhập số tài khoản nhận tiền...",
    accountMin: 6,
    accountMax: 20,
  },
  {
    value: "MOMO",
    label: methodName("MOMO"),
    hint: "Số điện thoại phải trùng với số đăng ký ví MoMo.",
    needsBank: false,
    accountLabel: "Số điện thoại ví MoMo",
    accountPlaceholder: "Nhập số điện thoại nhận tiền...",
    accountMin: 9,
    accountMax: 11,
  },
];

export function methodSpec(value: string): MethodSpec {
  return PAYOUT_METHODS.find((item) => item.value === value) ?? PAYOUT_METHODS[0];
}

export type Bank = { code: string; name: string; short: string };

/** Các ngân hàng phổ biến tại Việt Nam, sắp theo tần suất sử dụng. */
export const BANKS: Bank[] = [
  { code: "VCB", short: "Vietcombank", name: "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)" },
  { code: "TCB", short: "Techcombank", name: "Ngân hàng TMCP Kỹ thương Việt Nam (Techcombank)" },
  { code: "MB", short: "MB Bank", name: "Ngân hàng TMCP Quân đội (MB Bank)" },
  { code: "VTB", short: "VietinBank", name: "Ngân hàng TMCP Công thương Việt Nam (VietinBank)" },
  { code: "BIDV", short: "BIDV", name: "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam (BIDV)" },
  { code: "ACB", short: "ACB", name: "Ngân hàng TMCP Á Châu (ACB)" },
  { code: "VPB", short: "VPBank", name: "Ngân hàng TMCP Việt Nam Thịnh Vượng (VPBank)" },
  { code: "TPB", short: "TPBank", name: "Ngân hàng TMCP Tiên Phong (TPBank)" },
  { code: "STB", short: "Sacombank", name: "Ngân hàng TMCP Sài Gòn Thương Tín (Sacombank)" },
  { code: "AGR", short: "Agribank", name: "Ngân hàng NN&PTNT Việt Nam (Agribank)" },
  { code: "HDB", short: "HDBank", name: "Ngân hàng TMCP Phát triển TP.HCM (HDBank)" },
  { code: "VIB", short: "VIB", name: "Ngân hàng TMCP Quốc tế Việt Nam (VIB)" },
  { code: "SHB", short: "SHB", name: "Ngân hàng TMCP Sài Gòn — Hà Nội (SHB)" },
  { code: "MSB", short: "MSB", name: "Ngân hàng TMCP Hàng hải Việt Nam (MSB)" },
  { code: "OCB", short: "OCB", name: "Ngân hàng TMCP Phương Đông (OCB)" },
  { code: "SEA", short: "SeABank", name: "Ngân hàng TMCP Đông Nam Á (SeABank)" },
  { code: "EIB", short: "Eximbank", name: "Ngân hàng TMCP Xuất Nhập khẩu Việt Nam (Eximbank)" },
  { code: "LPB", short: "LPBank", name: "Ngân hàng TMCP Lộc Phát Việt Nam (LPBank)" },
  { code: "NAB", short: "Nam A Bank", name: "Ngân hàng TMCP Nam Á (Nam A Bank)" },
  { code: "ABB", short: "ABBANK", name: "Ngân hàng TMCP An Bình (ABBANK)" },
  { code: "BAB", short: "BacA Bank", name: "Ngân hàng TMCP Bắc Á (BacA Bank)" },
  { code: "PVC", short: "PVcomBank", name: "Ngân hàng TMCP Đại Chúng Việt Nam (PVcomBank)" },
  { code: "VAB", short: "VietABank", name: "Ngân hàng TMCP Việt Á (VietABank)" },
  { code: "SCB", short: "SCB", name: "Ngân hàng TMCP Sài Gòn (SCB)" },
  { code: "CAKE", short: "CAKE by VPBank", name: "Ngân hàng số CAKE by VPBank" },
  { code: "TIMO", short: "Timo", name: "Ngân hàng số Timo by BVBank" },
];

export function bankByCode(code: string): Bank | undefined {
  return BANKS.find((bank) => bank.code === code);
}

/**
 * Chuẩn hoá tên chủ tài khoản về IN HOA KHÔNG DẤU.
 *
 * Ngân hàng đối chiếu tên theo dạng không dấu, nên gõ tiếng Việt có dấu là
 * nguyên nhân sai lệnh chuyển khoản phổ biến nhất. Chuẩn hoá ngay khi gõ để
 * người dùng thấy đúng thứ sẽ được gửi đi.
 */
export function toPlainUpper(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // bỏ dấu thanh và dấu mũ
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toUpperCase()
    .replace(/[^A-Z\s]/g, "")
    .replace(/\s+/g, " ")
    .trimStart();
}

/** Chỉ giữ chữ số cho ô số tài khoản / số điện thoại. */
export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

export const formatVnd = (value: string | number) =>
  `${Number(value || 0).toLocaleString("vi-VN")}₫`;

/* -------------------------------------------------------------------------- */
/* Sổ tài khoản đã lưu — chỉ lưu trên máy người dùng                           */
/* -------------------------------------------------------------------------- */

export type SavedPayoutAccount = {
  id: string;
  method: PayoutMethod;
  bankCode?: string;
  accountNumber: string;
  accountName: string;
};

/**
 * Backend chưa có bảng sổ tài khoản nhận tiền, nên danh sách này nằm ở
 * localStorage và tách theo từng user để hai tài khoản dùng chung máy không
 * thấy thông tin của nhau. Hệ quả: đổi máy/trình duyệt là mất — cần chuyển
 * sang API khi backend bổ sung endpoint.
 */
const storageKey = (userId: number | string) => `bee_payout_accounts_v1_${userId}`;

export function loadSavedAccounts(
  userId: number | string,
): SavedPayoutAccount[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(storageKey(userId));
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as SavedPayoutAccount[]) : [];
  } catch {
    return [];
  }
}

export function persistSavedAccounts(
  userId: number | string,
  accounts: SavedPayoutAccount[],
): void {
  localStorage.setItem(storageKey(userId), JSON.stringify(accounts));
}

export function accountKey(account: Omit<SavedPayoutAccount, "id">): string {
  return [account.method, account.bankCode ?? "", account.accountNumber].join("|");
}

export function describeAccount(account: SavedPayoutAccount): string {
  const bank = account.bankCode ? bankByCode(account.bankCode)?.short : undefined;
  return [bank ?? methodSpec(account.method).label, account.accountNumber]
    .filter(Boolean)
    .join(" · ");
}
