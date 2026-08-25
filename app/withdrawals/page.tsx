"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";
import { errorMessage } from "@/lib/api";
import {
  BANKS,
  MIN_WITHDRAWAL,
  PAYOUT_METHODS,
  WITHDRAWAL_FEE,
  accountKey,
  bankByCode,
  describeAccount,
  digitsOnly,
  formatVnd,
  loadSavedAccounts,
  methodSpec,
  persistSavedAccounts,
  toPlainUpper,
  type PayoutMethod,
  type SavedPayoutAccount,
} from "@/lib/payout";
import {
  TONE_COLORS,
  WITHDRAWAL_STATUS_META,
  statusLabel,
  statusTone,
} from "@/lib/status";
import { theme, ui } from "@/lib/theme";
import { useAuth } from "../components/auth-context";
import SignInPrompt from "../components/sign-in-prompt";

type Withdrawal = {
  id: number;
  amount: string;
  method: string;
  bank_code?: string | null;
  bank_name?: string | null;
  account_name: string;
  account_number: string;
  status: string;
  requested_at: string;
  rejection_reason?: string | null;
};

type Wallet = { available_balance: string; pending_balance: string };

type Transaction = { transaction_type: string; amount: string };

/** Mức rút gợi ý, lọc bỏ mức vượt số dư để không mời gọi thao tác chắc chắn lỗi. */
const QUICK_AMOUNTS = [30_000, 50_000, 100_000, 200_000, 500_000];

export default function WithdrawalsPage() {
  const { signedIn, ready, account, request } = useAuth();

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [items, setItems] = useState<Withdrawal[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [savedAccounts, setSavedAccounts] = useState<SavedPayoutAccount[]>([]);

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PayoutMethod>("BANK");
  const [bankCode, setBankCode] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [accountName, setAccountName] = useState("");
  const [remember, setRemember] = useState(true);

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const spec = methodSpec(method);
  const available = Number(wallet?.available_balance ?? 0);
  const pending = Number(wallet?.pending_balance ?? 0);
  const amountValue = Number(amount || 0);

  const load = useCallback(async () => {
    const [nextWallet, nextItems, nextTransactions] = await Promise.all([
      request<Wallet>("/wallet"),
      request<Withdrawal[]>("/withdrawals"),
      request<Transaction[]>("/wallet/transactions"),
    ]);
    setWallet(nextWallet);
    setItems(nextItems);
    setTransactions(nextTransactions);
  }, [request]);

  useEffect(() => {
    if (!signedIn) return;
    load().catch((loadError) =>
      setError(errorMessage(loadError, "Không tải được dữ liệu ví")),
    );
  }, [signedIn, load]);

  useEffect(() => {
    if (account) setSavedAccounts(loadSavedAccounts(account.id));
  }, [account]);

  /**
   * "Đã tích luỹ" = tổng cashback đã duyệt trừ phần bị thu hồi (bản ghi thu hồi
   * mang số âm nên cộng dồn là đúng). "Đã giải ngân" chỉ tính các lệnh rút đã
   * chi trả xong, không tính lệnh đang chờ duyệt.
   */
  const earned = useMemo(
    () =>
      transactions
        .filter((tx) =>
          ["CASHBACK_APPROVED", "CASHBACK_REVERSED"].includes(
            tx.transaction_type,
          ),
        )
        .reduce((total, tx) => total + Number(tx.amount || 0), 0),
    [transactions],
  );

  const disbursed = useMemo(
    () =>
      items
        .filter((item) => item.status === "COMPLETED")
        .reduce((total, item) => total + Number(item.amount || 0), 0),
    [items],
  );

  const pendingRequests = items.filter((item) =>
    ["PENDING", "PROCESSING"].includes(item.status),
  ).length;

  /** Lý do chưa gửi được, hiện ngay dưới nút thay vì để bấm rồi mới báo lỗi. */
  const blocker = useMemo(() => {
    if (!amountValue) return "Nhập số tiền cần rút.";
    if (amountValue < MIN_WITHDRAWAL)
      return `Số tiền tối thiểu là ${formatVnd(MIN_WITHDRAWAL)}.`;
    if (amountValue > available)
      return `Vượt số dư khả dụng (${formatVnd(available)}).`;
    if (spec.needsBank && !bankCode) return "Chọn ngân hàng nhận tiền.";
    if (accountNumber.length < spec.accountMin)
      return `${spec.accountLabel} chưa hợp lệ.`;
    if (accountName.trim().length < 2) return "Nhập họ tên chủ tài khoản.";
    return "";
  }, [amountValue, available, spec, bankCode, accountNumber, accountName]);

  function applySaved(saved: SavedPayoutAccount) {
    setMethod(saved.method);
    setBankCode(saved.bankCode ?? "");
    setAccountNumber(saved.accountNumber);
    setAccountName(saved.accountName);
    setMessage("");
    setError("");
  }

  function forgetSaved(id: string) {
    if (!account) return;
    const next = savedAccounts.filter((item) => item.id !== id);
    setSavedAccounts(next);
    persistSavedAccounts(account.id, next);
  }

  function rememberAccount() {
    if (!account) return;
    const draft = {
      method,
      bankCode: spec.needsBank ? bankCode : undefined,
      accountNumber,
      accountName,
    };
    const key = accountKey(draft);
    const next = [
      { ...draft, id: key },
      ...savedAccounts.filter((item) => accountKey(item) !== key),
    ].slice(0, 5);
    setSavedAccounts(next);
    persistSavedAccounts(account.id, next);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (blocker) {
      setError(blocker);
      return;
    }
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const created = await request<Withdrawal>("/withdrawals", {
        method: "POST",
        body: {
          amount: amountValue,
          method,
          bank_code: spec.needsBank ? bankCode : null,
          bank_name: spec.needsBank ? bankByCode(bankCode)?.short : null,
          account_name: accountName.trim(),
          account_number: accountNumber,
        },
      });
      setItems((current) => [created, ...current]);
      if (remember) rememberAccount();
      setAmount("");
      setMessage(
        `Đã gửi yêu cầu rút ${formatVnd(amountValue)}. Admin sẽ duyệt trong 1–24 giờ làm việc.`,
      );
      // Số dư khả dụng bị giữ lại ngay khi tạo lệnh nên phải đọc lại ví.
      await load();
    } catch (submitError) {
      setError(errorMessage(submitError, "Không thể tạo yêu cầu"));
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return <main style={ui.shell}>Đang tải…</main>;
  if (!signedIn)
    return (
      <SignInPrompt
        title="Rút tiền hoàn"
        text="Đăng nhập để tạo lệnh rút và theo dõi trạng thái chi trả. Trang chủ vẫn mở ngay phía sau."
      />
    );

  return (
    <main style={ui.shell}>
      <p style={ui.kicker}>Ví của tôi</p>
      <h1 style={ui.h1}>Tạo lệnh rút tiền</h1>

      <div style={styles.layout}>
        {/* ------------------------------ Cột trái ------------------------------ */}
        <form onSubmit={submit} style={styles.formColumn}>
          <section style={ui.panel}>
            <div style={styles.panelHead}>
              <h2 style={ui.h2}>Sổ tài khoản đã lưu</h2>
              <label style={styles.remember}>
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                Lưu tài khoản này
              </label>
            </div>

            {savedAccounts.length ? (
              <div style={styles.savedList}>
                {savedAccounts.map((saved) => {
                  const active =
                    saved.accountNumber === accountNumber &&
                    saved.method === method &&
                    (saved.bankCode ?? "") === bankCode;
                  return (
                    <div
                      key={saved.id}
                      style={{
                        ...styles.savedCard,
                        ...(active ? styles.savedCardActive : {}),
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => applySaved(saved)}
                        style={styles.savedPick}
                      >
                        <strong style={{ fontSize: 14 }}>
                          {describeAccount(saved)}
                        </strong>
                        <small style={styles.savedName}>
                          {saved.accountName}
                        </small>
                      </button>
                      <button
                        type="button"
                        onClick={() => forgetSaved(saved.id)}
                        aria-label={`Xoá ${describeAccount(saved)}`}
                        style={styles.savedRemove}
                      >
                        ×
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p style={styles.savedEmpty}>
                Chưa có tài khoản nào được lưu. Điền thông tin nhận tiền bên dưới
                rồi bấm <strong>“Lưu tài khoản này”</strong> để dùng nhanh cho
                lần sau.
              </p>
            )}
          </section>

          <section style={{ ...ui.panel, display: "grid", gap: 18 }}>
            <label style={ui.field}>
              Số tiền cần rút (VND)
              <input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(digitsOnly(event.target.value))}
                placeholder="Ví dụ: 30000"
                style={ui.input}
              />
              <div style={styles.quickRow}>
                {QUICK_AMOUNTS.filter((value) => value <= available).map(
                  (value) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setAmount(String(value))}
                      style={styles.quick}
                    >
                      {formatVnd(value)}
                    </button>
                  ),
                )}
                {available >= MIN_WITHDRAWAL && (
                  <button
                    type="button"
                    onClick={() => setAmount(String(Math.floor(available)))}
                    style={{ ...styles.quick, ...styles.quickMax }}
                  >
                    Rút toàn bộ
                  </button>
                )}
              </div>
              <small style={styles.hint}>
                Số tiền tối thiểu: <strong>{formatVnd(MIN_WITHDRAWAL)}</strong> |
                Phí rút:{" "}
                <strong>
                  {WITHDRAWAL_FEE ? formatVnd(WITHDRAWAL_FEE) : "Miễn phí"}
                </strong>
              </small>
              {amountValue > 0 && amountValue <= available && (
                <small style={styles.hint}>
                  Số dư còn lại sau khi rút:{" "}
                  <strong>{formatVnd(available - amountValue)}</strong>
                </small>
              )}
            </label>

            <fieldset style={styles.fieldset}>
              <legend style={ui.field}>Hình thức nhận tiền</legend>
              <div style={styles.methodRow}>
                {PAYOUT_METHODS.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      setMethod(item.value);
                      setAccountNumber("");
                      if (!item.needsBank) setBankCode("");
                    }}
                    style={{
                      ...styles.methodCard,
                      ...(method === item.value ? styles.methodActive : {}),
                    }}
                  >
                    <strong>{item.label}</strong>
                    <small style={styles.methodHint}>{item.hint}</small>
                  </button>
                ))}
              </div>
            </fieldset>

            {spec.needsBank && (
              <label style={ui.field}>
                Tên ngân hàng nhận
                <select
                  value={bankCode}
                  onChange={(event) => setBankCode(event.target.value)}
                  style={ui.input}
                >
                  <option value="">-- Chọn ngân hàng nhận --</option>
                  {BANKS.map((bank) => (
                    <option key={bank.code} value={bank.code}>
                      {bank.name}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <label style={ui.field}>
              {spec.accountLabel}
              <input
                inputMode="numeric"
                value={accountNumber}
                onChange={(event) =>
                  setAccountNumber(
                    digitsOnly(event.target.value).slice(0, spec.accountMax),
                  )
                }
                placeholder={spec.accountPlaceholder}
                style={ui.input}
              />
            </label>

            <label style={ui.field}>
              Họ tên chủ tài khoản
              <input
                value={accountName}
                onChange={(event) =>
                  setAccountName(toPlainUpper(event.target.value))
                }
                placeholder="VIET HOA KHONG DAU (Ví dụ: NGUYEN VAN A)..."
                style={{ ...ui.input, letterSpacing: "0.04em" }}
              />
              <small style={styles.hint}>
                Tự động chuyển sang IN HOA không dấu khi bạn gõ.
              </small>
            </label>

            <button
              type="submit"
              disabled={busy || Boolean(blocker)}
              style={{
                ...ui.btnPrimary,
                width: "100%",
                ...(busy || blocker ? styles.submitDisabled : {}),
              }}
            >
              {busy ? "Đang gửi yêu cầu..." : "Gửi yêu cầu rút tiền"}
            </button>

            {blocker && !error && <small style={styles.hint}>{blocker}</small>}
            {message && <p style={styles.success}>{message}</p>}
            {error && <p style={ui.error}>{error}</p>}
          </section>

          <section style={ui.panel}>
            <h2 style={{ ...ui.h2, marginBottom: 10 }}>Lịch sử rút tiền</h2>
            {items.length ? (
              items.map((item) => (
                <div key={item.id} style={ui.row}>
                  <div style={{ minWidth: 0 }}>
                    <strong>{formatVnd(item.amount)}</strong>
                    <small style={styles.small}>
                      {item.bank_name ?? methodSpec(item.method).label} ·{" "}
                      {item.account_number} ·{" "}
                      {new Date(item.requested_at).toLocaleDateString("vi-VN")}
                    </small>
                    {item.rejection_reason && (
                      <small style={styles.small}>
                        Lý do: {item.rejection_reason}
                      </small>
                    )}
                  </div>
                  <span
                    style={{
                      ...ui.badge,
                      ...TONE_COLORS[
                        statusTone(WITHDRAWAL_STATUS_META, item.status)
                      ],
                    }}
                  >
                    {statusLabel(WITHDRAWAL_STATUS_META, item.status)}
                  </span>
                </div>
              ))
            ) : (
              <p style={ui.empty}>Chưa có yêu cầu rút tiền nào.</p>
            )}
          </section>
        </form>

        {/* ------------------------------ Cột phải ------------------------------ */}
        <aside style={styles.sidebar}>
          <section style={styles.balanceCard}>
            <span style={{ color: theme.onDarkSoft, fontSize: 14 }}>
              Số dư ví hiện tại
            </span>
            <strong style={styles.balanceAmount}>{formatVnd(available)}</strong>

            <div style={styles.balanceSplit}>
              <div>
                <small style={{ color: theme.onDarkSoft }}>Đã tích luỹ</small>
                <strong style={styles.balanceSub}>{formatVnd(earned)}</strong>
              </div>
              <div>
                <small style={{ color: theme.onDarkSoft }}>Đã giải ngân</small>
                <strong style={styles.balanceSub}>{formatVnd(disbursed)}</strong>
              </div>
            </div>

            <div style={styles.balanceFoot}>
              <span>Đang chờ hoàn</span>
              <strong style={{ color: theme.accent }}>
                {formatVnd(pending)}
              </strong>
            </div>
            {pendingRequests > 0 && (
              <p style={styles.pendingNote}>
                Bạn có <strong>{pendingRequests}</strong> lệnh rút đang chờ Admin
                duyệt.
              </p>
            )}
          </section>

          <section style={ui.panel}>
            <h2 style={{ ...ui.h2, marginBottom: 12 }}>Quy định rút tiền</h2>
            <ol style={styles.rules}>
              <li>
                Vui lòng nhập đúng số tài khoản ngân hàng và viết{" "}
                <strong>IN HOA, không dấu</strong> tên chủ tài khoản. Hệ thống xử
                lý rút tiền theo thông tin người dùng cung cấp và không chịu trách
                nhiệm nếu giao dịch sai do người dùng nhập sai thông tin.
              </li>
              <li>
                Yêu cầu rút tiền được Admin kiểm tra và duyệt thủ công trong vòng{" "}
                <strong>1–24 giờ làm việc</strong>.
              </li>
              <li>
                Tài khoản gian lận, lạm dụng điểm danh, tạo đơn ảo hoặc vi phạm
                quy định sẽ bị <strong>khoá vĩnh viễn</strong> và có thể bị huỷ số
                dư ví.
              </li>
            </ol>
          </section>
        </aside>
      </div>
    </main>
  );
}

const styles: Record<string, CSSProperties> = {
  layout: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.35fr) minmax(280px, 0.65fr)",
    gap: 18,
    marginTop: 30,
    alignItems: "start",
  },
  formColumn: { display: "grid", gap: 16 },
  sidebar: { display: "grid", gap: 16, position: "sticky", top: 92 },

  panelHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 10,
    marginBottom: 14,
  },
  remember: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    color: theme.inkSoft,
    fontSize: 14,
    fontWeight: 700,
    cursor: "pointer",
  },
  savedList: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))",
    gap: 10,
  },
  savedCard: {
    display: "flex",
    alignItems: "stretch",
    gap: 4,
    borderRadius: 16,
    background: "rgba(255,255,255,0.62)",
    border: "1px solid rgba(80, 48, 0, 0.14)",
    overflow: "hidden",
  },
  savedCardActive: {
    border: `1px solid ${theme.accentLine}`,
    background: "rgba(255, 201, 40, 0.22)",
  },
  savedPick: {
    flex: 1,
    display: "grid",
    gap: 4,
    padding: "12px 14px",
    border: 0,
    background: "transparent",
    color: theme.ink,
    textAlign: "left",
    fontFamily: "inherit",
    cursor: "pointer",
    minWidth: 0,
  },
  savedName: {
    color: theme.inkMuted,
    fontSize: 12,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  savedRemove: {
    width: 34,
    border: 0,
    background: "transparent",
    color: theme.inkFaint,
    fontSize: 19,
    cursor: "pointer",
  },
  savedEmpty: {
    margin: 0,
    color: theme.inkMuted,
    fontSize: 14,
    lineHeight: 1.65,
  },

  quickRow: { display: "flex", flexWrap: "wrap", gap: 8 },
  quick: {
    borderRadius: 999,
    padding: "8px 14px",
    border: "1px solid rgba(80, 48, 0, 0.16)",
    background: "rgba(255,255,255,0.6)",
    color: theme.inkSoft,
    fontSize: 13,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  quickMax: {
    background: "rgba(255, 201, 40, 0.28)",
    color: "#6d4500",
    border: "1px solid rgba(201, 130, 0, 0.4)",
  },
  hint: {
    color: theme.inkMuted,
    fontSize: 13,
    fontWeight: 500,
  },

  fieldset: { margin: 0, padding: 0, border: 0 },
  methodRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: 10,
    marginTop: 8,
  },
  methodCard: {
    display: "grid",
    gap: 5,
    padding: "14px 16px",
    borderRadius: 16,
    border: "1px solid rgba(80, 48, 0, 0.14)",
    background: "rgba(255,255,255,0.6)",
    color: theme.ink,
    textAlign: "left",
    fontFamily: "inherit",
    fontSize: 15,
    cursor: "pointer",
  },
  methodActive: {
    border: `1px solid ${theme.accentLine}`,
    background: "rgba(255, 201, 40, 0.26)",
    boxShadow: "0 12px 26px rgba(201, 130, 0, 0.16)",
  },
  methodHint: { color: theme.inkMuted, fontSize: 12, lineHeight: 1.5 },

  submitDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
    boxShadow: "none",
  },
  success: { margin: 0, color: "#159366", fontWeight: 700 },
  small: {
    display: "block",
    marginTop: 5,
    color: theme.inkMuted,
    fontSize: 13,
  },

  balanceCard: {
    display: "grid",
    gap: 6,
    padding: 24,
    borderRadius: 26,
    background: theme.dark,
    color: theme.onDark,
    boxShadow: "0 32px 90px rgba(114, 72, 8, 0.18)",
  },
  balanceAmount: {
    fontSize: 40,
    lineHeight: 1.05,
    letterSpacing: "-0.05em",
    fontWeight: 900,
    fontVariantNumeric: "tabular-nums",
  },
  balanceSplit: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginTop: 18,
    paddingTop: 16,
    borderTop: "1px solid rgba(255,255,255,0.1)",
  },
  balanceSub: {
    display: "block",
    marginTop: 4,
    fontSize: 17,
    fontVariantNumeric: "tabular-nums",
  },
  balanceFoot: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    marginTop: 16,
    paddingTop: 14,
    borderTop: "1px solid rgba(255,255,255,0.1)",
    color: "#ead9b9",
  },
  pendingNote: {
    margin: "14px 0 0",
    padding: "10px 12px",
    borderRadius: 14,
    background: "rgba(255, 201, 40, 0.16)",
    color: theme.accent,
    fontSize: 13,
  },
  rules: {
    margin: 0,
    paddingLeft: 20,
    display: "grid",
    gap: 12,
    color: theme.inkSoft,
    fontSize: 14,
    lineHeight: 1.7,
  },
};
