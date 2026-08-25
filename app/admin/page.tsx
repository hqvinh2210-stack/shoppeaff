"use client";

import {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { ApiError, errorMessage } from "@/lib/api";
import { formatVnd } from "@/lib/payout";
import {
  CASHBACK_STATUS_META,
  ORDER_STATUS_META,
  TONE_COLORS,
  WITHDRAWAL_STATUS_META,
  statusLabel,
  statusTone,
} from "@/lib/status";
import { theme, ui } from "@/lib/theme";
import { useAuth } from "../components/auth-context";
import SignInPrompt from "../components/sign-in-prompt";

type Summary = {
  users: number;
  pending_withdrawals: number;
  attribution_review_orders: number;
  total_available_balance: string | number;
  total_pending_balance: string | number;
};

type Report = {
  year: number;
  month: number;
  total_cashback: string | number;
  users: Array<{
    user_id: number;
    net_cashback: string | number;
    transactions: number;
  }>;
};

type AdminUser = {
  id: number;
  user_code: string;
  email?: string | null;
  phone?: string | null;
  full_name?: string | null;
  role: string;
  status: string;
  available_balance: string | number;
  pending_balance: string | number;
};

type AdminOrder = {
  id: number;
  user_id: number | null;
  platform_order_id: string;
  tracking_id?: string | null;
  order_status: string;
  commission_status: string;
  cashback_status: string;
  cashback_amount: string | number;
};

type AdminWithdrawal = {
  id: number;
  user_id: number;
  amount: string;
  method: string;
  bank_name?: string | null;
  account_name: string;
  account_number: string;
  status: string;
  requested_at: string;
  rejection_reason?: string | null;
};

type ReviewOrder = {
  id: number;
  platform: string;
  platform_order_id: string;
  tracking_id?: string | null;
  commission_amount: string | number;
  cashback_status: string;
};

const TABS = [
  { key: "report", label: "Báo cáo tháng" },
  { key: "withdrawals", label: "Duyệt rút tiền" },
  { key: "review", label: "Chờ đối soát" },
  { key: "orders", label: "Đơn hàng" },
  { key: "users", label: "Người dùng" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function AdminPage() {
  const { signedIn, ready, isAdmin, account, request } = useAuth();
  const now = new Date();

  const [tab, setTab] = useState<TabKey>("report");
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const [summary, setSummary] = useState<Summary | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [withdrawals, setWithdrawals] = useState<AdminWithdrawal[]>([]);
  const [review, setReview] = useState<ReviewOrder[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const describeError = useCallback(
    (caught: unknown, fallback: string) =>
      caught instanceof ApiError && caught.isForbidden
        ? "Tài khoản này không có quyền quản trị."
        : errorMessage(caught, fallback),
    [],
  );

  const loadReport = useCallback(
    async (selectedYear: number, selectedMonth: number) => {
      setLoading(true);
      setError("");
      try {
        setReport(
          await request<Report>(
            `/admin/cashback/monthly?year=${selectedYear}&month=${selectedMonth}`,
          ),
        );
      } catch (caught) {
        setReport(null);
        setError(describeError(caught, "Không tải được báo cáo"));
      } finally {
        setLoading(false);
      }
    },
    [request, describeError],
  );

  /** Nạp lại tất cả bảng quản trị; gọi sau mỗi thao tác duyệt/từ chối. */
  const loadAll = useCallback(async () => {
    setError("");
    try {
      const [nextSummary, nextUsers, nextOrders, nextWithdrawals, nextReview] =
        await Promise.all([
          request<Summary>("/admin/summary"),
          request<AdminUser[]>("/admin/users"),
          request<AdminOrder[]>("/admin/orders"),
          request<AdminWithdrawal[]>("/admin/withdrawals"),
          request<ReviewOrder[]>("/admin/orders/attribution-review"),
        ]);
      setSummary(nextSummary);
      setUsers(nextUsers);
      setOrders(nextOrders);
      setWithdrawals(nextWithdrawals);
      setReview(nextReview);
    } catch (caught) {
      setError(describeError(caught, "Không tải được dữ liệu quản trị"));
    }
  }, [request, describeError]);

  useEffect(() => {
    if (!signedIn) return;
    void loadAll();
    void loadReport(year, month);
    // Chỉ nạp lần đầu; đổi kỳ báo cáo là thao tác bấm nút của người dùng.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signedIn]);

  async function approve(withdrawal: AdminWithdrawal) {
    if (
      !window.confirm(
        `Xác nhận ĐÃ CHUYỂN ${formatVnd(withdrawal.amount)} cho ${withdrawal.account_name} (${withdrawal.account_number})?`,
      )
    )
      return;
    setNotice("");
    try {
      await request(`/admin/withdrawals/${withdrawal.id}/approve`, {
        method: "POST",
      });
      setNotice(`Đã duyệt lệnh rút #${withdrawal.id}.`);
      await loadAll();
    } catch (caught) {
      setError(describeError(caught, "Không duyệt được yêu cầu"));
    }
  }

  async function reject(withdrawal: AdminWithdrawal) {
    const reason = window.prompt(
      `Lý do từ chối lệnh rút #${withdrawal.id} (${formatVnd(withdrawal.amount)}):`,
    );
    if (reason === null) return;
    if (reason.trim().length < 3) {
      setError("Lý do từ chối phải có tối thiểu 3 ký tự.");
      return;
    }
    setNotice("");
    try {
      await request(`/admin/withdrawals/${withdrawal.id}/reject`, {
        method: "POST",
        body: { reason: reason.trim() },
      });
      setNotice(`Đã từ chối lệnh rút #${withdrawal.id}, tiền đã hoàn về ví.`);
      await loadAll();
    } catch (caught) {
      setError(describeError(caught, "Không từ chối được yêu cầu"));
    }
  }

  if (!ready) return <main style={ui.shell}>Đang tải…</main>;
  if (!signedIn)
    return (
      <SignInPrompt
        title="Báo cáo vận hành"
        text="Khu vực dành cho tài khoản quản trị. Đăng nhập để xem số liệu và duyệt yêu cầu rút tiền."
      />
    );

  const pendingWithdrawals = withdrawals.filter(
    (item) => !["COMPLETED", "REJECTED"].includes(item.status),
  );

  return (
    <main style={ui.shell}>
      <p style={ui.kicker}>Báo cáo vận hành</p>
      <h1 style={ui.h1}>Bảng điều khiển quản trị</h1>
      <p style={ui.lead}>
        Đang đăng nhập: <strong>{account?.email ?? account?.user_code}</strong>
        {!isAdmin && " — tài khoản này chưa có quyền quản trị."}
      </p>

      {summary && (
        <div style={styles.summaryGrid}>
          <SummaryCard label="Tài khoản" value={String(summary.users)} />
          <SummaryCard
            label="Lệnh rút chờ duyệt"
            value={String(summary.pending_withdrawals)}
            highlight={summary.pending_withdrawals > 0}
          />
          <SummaryCard
            label="Đơn chờ quy gán"
            value={String(summary.attribution_review_orders)}
            highlight={summary.attribution_review_orders > 0}
          />
          <SummaryCard
            label="Tổng ví khả dụng"
            value={formatVnd(summary.total_available_balance)}
          />
          <SummaryCard
            label="Tổng chờ hoàn"
            value={formatVnd(summary.total_pending_balance)}
          />
        </div>
      )}

      <div style={styles.tabs}>
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            style={{
              ...styles.tab,
              ...(tab === item.key ? styles.tabActive : {}),
            }}
          >
            {item.label}
            {item.key === "withdrawals" && pendingWithdrawals.length > 0 && (
              <span style={styles.count}>{pendingWithdrawals.length}</span>
            )}
            {item.key === "review" && review.length > 0 && (
              <span style={styles.count}>{review.length}</span>
            )}
          </button>
        ))}
      </div>

      {notice && <p style={styles.success}>{notice}</p>}
      {error && <p style={ui.error}>{error}</p>}

      {tab === "report" && (
        <section style={{ ...ui.panel, marginTop: 16 }}>
          <div style={styles.filters}>
            <label style={ui.field}>
              Năm
              <select
                value={year}
                onChange={(event) => setYear(Number(event.target.value))}
                style={ui.input}
              >
                {Array.from(
                  { length: 6 },
                  (_, index) => now.getFullYear() - index,
                ).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label style={ui.field}>
              Tháng
              <select
                value={month}
                onChange={(event) => setMonth(Number(event.target.value))}
                style={ui.input}
              >
                {Array.from({ length: 12 }, (_, index) => index + 1).map(
                  (value) => (
                    <option key={value} value={value}>
                      Tháng {value}
                    </option>
                  ),
                )}
              </select>
            </label>
            <button
              type="button"
              onClick={() => void loadReport(year, month)}
              disabled={loading}
              style={ui.btnPrimary}
            >
              {loading ? "Đang tải..." : "Xem báo cáo"}
            </button>
          </div>

          {report && (
            <>
              <div style={styles.reportTotal}>
                <span>
                  Tổng hoàn tháng {report.month}/{report.year}
                </span>
                <strong>{formatVnd(report.total_cashback)}</strong>
              </div>
              {report.users.length ? (
                report.users.map((row) => (
                  <div key={row.user_id} style={ui.row}>
                    <span>Tài khoản #{row.user_id}</span>
                    <span style={styles.muted}>
                      {row.transactions} giao dịch
                    </span>
                    <strong>{formatVnd(row.net_cashback)}</strong>
                  </div>
                ))
              ) : (
                <p style={ui.empty}>Chưa có cashback trong tháng này.</p>
              )}
            </>
          )}
        </section>
      )}

      {tab === "withdrawals" && (
        <section style={{ ...ui.panel, marginTop: 16 }}>
          <h2 style={{ ...ui.h2, marginBottom: 10 }}>Yêu cầu rút tiền</h2>
          {withdrawals.length ? (
            withdrawals.map((item) => (
              <div key={item.id} style={styles.withdrawalRow}>
                <div style={{ minWidth: 0 }}>
                  <strong>
                    #{item.id} · {formatVnd(item.amount)}
                  </strong>
                  <small style={styles.small}>
                    Tài khoản #{item.user_id} ·{" "}
                    {new Date(item.requested_at).toLocaleString("vi-VN")}
                  </small>
                  <small style={styles.small}>
                    {item.bank_name ?? item.method} · {item.account_number} ·{" "}
                    <strong>{item.account_name}</strong>
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
                <div style={styles.actions}>
                  {["COMPLETED", "REJECTED"].includes(item.status) ? (
                    <span style={styles.muted}>Đã xử lý</span>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => void approve(item)}
                        style={styles.approve}
                      >
                        Đã chuyển
                      </button>
                      <button
                        type="button"
                        onClick={() => void reject(item)}
                        style={styles.reject}
                      >
                        Từ chối
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))
          ) : (
            <p style={ui.empty}>Chưa có yêu cầu rút tiền nào.</p>
          )}
        </section>
      )}

      {tab === "review" && (
        <section style={{ ...ui.panel, marginTop: 16 }}>
          <h2 style={{ ...ui.h2, marginBottom: 6 }}>Đơn chờ quy gán</h2>
          <p style={styles.muted}>
            Đơn về từ mạng affiliate nhưng không khớp `tracking_id` nào — chưa có
            chủ và chưa được cộng tiền hoàn.
          </p>
          {review.length ? (
            review.map((item) => (
              <div key={item.id} style={ui.row}>
                <div style={{ minWidth: 0 }}>
                  <strong>{item.platform_order_id}</strong>
                  <small style={styles.small}>
                    {item.platform} · tracking: {item.tracking_id || "(trống)"}
                  </small>
                </div>
                <strong>{formatVnd(item.commission_amount)}</strong>
                <span
                  style={{
                    ...ui.badge,
                    ...TONE_COLORS[
                      statusTone(CASHBACK_STATUS_META, item.cashback_status)
                    ],
                  }}
                >
                  {statusLabel(CASHBACK_STATUS_META, item.cashback_status)}
                </span>
              </div>
            ))
          ) : (
            <p style={ui.empty}>Không có đơn nào cần đối soát.</p>
          )}
        </section>
      )}

      {tab === "orders" && (
        <section style={{ ...ui.panel, marginTop: 16 }}>
          <h2 style={{ ...ui.h2, marginBottom: 10 }}>
            Đơn hàng gần nhất ({orders.length})
          </h2>
          {orders.length ? (
            orders.map((item) => (
              <div key={item.id} style={ui.row}>
                <div style={{ minWidth: 0 }}>
                  <strong>{item.platform_order_id}</strong>
                  <small style={styles.small}>
                    {item.user_id
                      ? `Tài khoản #${item.user_id}`
                      : "Chưa có chủ"}{" "}
                    · tracking: {item.tracking_id || "(trống)"}
                  </small>
                </div>
                <span
                  style={{
                    ...ui.badge,
                    ...TONE_COLORS[
                      statusTone(ORDER_STATUS_META, item.order_status)
                    ],
                  }}
                >
                  {statusLabel(ORDER_STATUS_META, item.order_status)}
                </span>
                <strong>{formatVnd(item.cashback_amount)}</strong>
              </div>
            ))
          ) : (
            <p style={ui.empty}>Chưa có đơn hàng nào.</p>
          )}
        </section>
      )}

      {tab === "users" && (
        <section style={{ ...ui.panel, marginTop: 16 }}>
          <h2 style={{ ...ui.h2, marginBottom: 10 }}>
            Người dùng ({users.length})
          </h2>
          {users.length ? (
            users.map((item) => (
              <div key={item.id} style={ui.row}>
                <div style={{ minWidth: 0 }}>
                  <strong>
                    {item.full_name || item.email || item.phone || item.user_code}
                  </strong>
                  <small style={styles.small}>
                    {item.user_code} · {item.email ?? item.phone ?? "—"}
                  </small>
                </div>
                {item.role === "ADMIN" && (
                  <span style={{ ...ui.badge, ...TONE_COLORS.success }}>
                    ADMIN
                  </span>
                )}
                <div style={{ textAlign: "right" }}>
                  <strong>{formatVnd(item.available_balance)}</strong>
                  <small style={styles.small}>
                    chờ hoàn {formatVnd(item.pending_balance)}
                  </small>
                </div>
              </div>
            ))
          ) : (
            <p style={ui.empty}>Chưa có người dùng nào.</p>
          )}
        </section>
      )}
    </main>
  );
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}): ReactNode {
  return (
    <div style={{ ...ui.metric, ...(highlight ? styles.metricAlert : {}) }}>
      <span style={{ color: theme.inkMuted, fontSize: 13 }}>{label}</span>
      <strong style={{ fontSize: 24, letterSpacing: "-0.04em" }}>{value}</strong>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
    gap: 12,
    marginTop: 28,
  },
  metricAlert: {
    background: "rgba(255, 201, 40, 0.3)",
    border: "1px solid rgba(201, 130, 0, 0.34)",
  },
  tabs: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
    marginTop: 24,
    padding: 5,
    borderRadius: 999,
    background: "rgba(255,255,255,0.55)",
    border: "1px solid rgba(80, 48, 0, 0.1)",
  },
  tab: {
    display: "inline-flex",
    alignItems: "center",
    gap: 7,
    border: 0,
    borderRadius: 999,
    padding: "10px 16px",
    background: "transparent",
    color: "#6d5227",
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  tabActive: {
    background: theme.dark,
    color: theme.onDark,
    fontWeight: 800,
  },
  count: {
    display: "inline-grid",
    placeItems: "center",
    minWidth: 20,
    height: 20,
    padding: "0 6px",
    borderRadius: 999,
    background: theme.accent,
    color: theme.ink,
    fontSize: 11,
    fontWeight: 900,
  },
  filters: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "end",
    gap: 14,
    marginBottom: 18,
  },
  reportTotal: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 16,
    padding: "18px 20px",
    marginBottom: 12,
    borderRadius: 20,
    background: theme.dark,
    color: theme.onDark,
    fontSize: 18,
    fontWeight: 800,
  },
  withdrawalRow: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.6fr) auto auto",
    alignItems: "center",
    gap: 14,
    padding: "16px 0",
    borderBottom: theme.divider,
  },
  actions: { display: "flex", gap: 8 },
  approve: {
    border: 0,
    borderRadius: 999,
    padding: "9px 15px",
    background: "#159366",
    color: "#fff",
    fontSize: 13,
    fontWeight: 800,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  reject: {
    borderRadius: 999,
    padding: "9px 15px",
    border: "1px solid rgba(196, 81, 66, 0.5)",
    background: "transparent",
    color: "#c45142",
    fontSize: 13,
    fontWeight: 800,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  small: {
    display: "block",
    marginTop: 4,
    color: theme.inkMuted,
    fontSize: 13,
  },
  muted: { color: theme.inkMuted, fontSize: 14 },
  success: { margin: "16px 0 0", color: "#159366", fontWeight: 700 },
};
