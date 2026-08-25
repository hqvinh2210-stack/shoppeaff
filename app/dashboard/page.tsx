"use client";

import { useCallback, useEffect, useMemo, useState, type CSSProperties, type FormEvent } from "react";
import { errorMessage } from "@/lib/api";
import {
  CASHBACK_FILTERS,
  CASHBACK_FILTER_LABELS,
  CASHBACK_STATUS_META,
  ORDER_STATUS_META,
  TONE_COLORS,
  TRANSACTION_STATUS_META,
  TRANSACTION_TYPE_META,
  statusLabel,
  statusTone,
  type CashbackFilter,
} from "@/lib/status";
import { theme, ui } from "@/lib/theme";
import { useAuth } from "../components/auth-context";
import ChannelLinks from "../components/channel-links";
import SignInPrompt from "../components/sign-in-prompt";

type Wallet = {
  available_balance: string;
  pending_balance: string;
  currency: string;
};

type Order = {
  id: number;
  platform_order_id: string;
  product_name?: string | null;
  order_amount: string;
  cashback_amount: string;
  order_status: string;
  cashback_status: string;
  created_at: string;
};

type AffiliateLinkRecord = {
  id: number;
  tracking_id: string;
  affiliate_url?: string | null;
  normalized_url: string;
};

type Transaction = {
  id: number;
  order_id: number | null;
  transaction_type: string;
  amount: string;
  balance_after: string;
  status: string;
  reference_code: string;
  created_at: string;
};

const money = (value: string | number) =>
  `${Number(value || 0).toLocaleString("vi-VN")}đ`;

export default function DashboardPage() {
  const { signedIn, ready, account, request } = useAuth();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [links, setLinks] = useState<AffiliateLinkRecord[]>([]);
  const [url, setUrl] = useState("");
  const [generated, setGenerated] = useState<AffiliateLinkRecord | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [openOrderId, setOpenOrderId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [filter, setFilter] = useState<CashbackFilter>("ALL");

  const load = useCallback(async () => {
    const [nextWallet, nextOrders, nextLinks, nextTransactions] = await Promise.all([
      request<Wallet>("/wallet"),
      request<Order[]>("/orders"),
      request<AffiliateLinkRecord[]>("/affiliate/links"),
      request<Transaction[]>("/wallet/transactions"),
    ]);
    setWallet(nextWallet);
    setOrders(nextOrders);
    setLinks(nextLinks);
    setTransactions(nextTransactions);
  }, [request]);

  useEffect(() => {
    if (!signedIn) return;
    load().catch((loadError) =>
      setMessage(errorMessage(loadError, "Không tải được dữ liệu tài khoản")),
    );
  }, [signedIn, load]);

  async function createLink(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    setGenerated(null);
    try {
      const link = await request<AffiliateLinkRecord>(
        "/affiliate/generate-link",
        { method: "POST", body: { original_url: url } },
      );
      setGenerated(link);
      setLinks((current) => [link, ...current]);
      setUrl("");
    } catch (createError) {
      setMessage(errorMessage(createError, "Không tạo được link"));
    }
  }

  const visibleOrders = useMemo(
    () =>
      orders.filter(
        (order) => filter === "ALL" || order.cashback_status === filter,
      ),
    [orders, filter],
  );

  if (!ready) return <main style={ui.shell}>Đang tải…</main>;
  if (!signedIn)
    return (
      <SignInPrompt
        title="Tổng quan tài khoản"
        text="Đăng nhập để xem ví, danh sách link tracking và các đơn hoàn tiền của bạn. Trang chủ vẫn mở ngay phía sau."
      />
    );

  const name = account?.full_name || account?.email || account?.user_code;

  return (
    <main style={ui.shell}>
      <p style={ui.kicker}>Tài khoản cá nhân</p>
      <h1 style={ui.h1}>Xin chào, {name}.</h1>
      <p style={ui.lead}>
        Theo dõi ví, link tracking và toàn bộ đơn hoàn tiền trong một màn hình.
      </p>

      {message && <p style={ui.error}>{message}</p>}

      <div style={styles.walletGrid}>
        <div style={styles.walletCard}>
          <div style={styles.walletHead}>
            <span style={{ fontWeight: 800 }}>Bee Wallet</span>
            <span style={styles.live}>{wallet?.currency ?? "VND"}</span>
          </div>
          <p style={{ margin: 0, color: theme.onDarkSoft, fontSize: 14 }}>
            Số dư khả dụng
          </p>
          <div style={styles.walletAmount}>
            {money(wallet?.available_balance ?? 0)}
          </div>
          <div style={styles.walletRow}>
            <span style={{ color: "#ead9b9" }}>Đang chờ hoàn</span>
            <strong style={{ color: theme.accent }}>
              {money(wallet?.pending_balance ?? 0)}
            </strong>
          </div>
          <a href="/withdrawals" style={styles.walletCta}>
            Tạo yêu cầu rút tiền
          </a>
        </div>

        <div style={{ display: "grid", gap: 14 }}>
          <form onSubmit={createLink} style={ui.panel}>
            <label style={ui.field}>
              Dán link Shopee để tạo link tracking
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                <input
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://shopee.vn/..."
                  required
                  style={{ ...ui.input, flex: "1 1 260px" }}
                />
                <button type="submit" style={ui.btnAccent}>
                  Tạo link
                </button>
              </div>
            </label>
            {generated && (
              <div style={styles.generated}>
                <strong>{generated.tracking_id}</strong>
                <br />
                {generated.affiliate_url}
              </div>
            )}
          </form>

          <ChannelLinks />
        </div>
      </div>

      <section style={{ marginTop: 42 }}>
        <div style={styles.sectionHead}>
          <h2 style={{ ...ui.h2, fontSize: 30 }}>Đơn hàng và tiền hoàn</h2>
          <div style={styles.filters}>
            {CASHBACK_FILTERS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setFilter(item)}
                style={{
                  ...styles.filter,
                  ...(filter === item ? styles.filterActive : {}),
                }}
              >
                {CASHBACK_FILTER_LABELS[item]}
              </button>
            ))}
          </div>
        </div>

        <p style={styles.notice}>
          ⓘ Đơn mới ghi nhận sẽ ở trạng thái chờ. Tiền hoàn chỉ chuyển sang số dư
          khả dụng sau khi hoa hồng được đối soát.
        </p>

        <div style={ui.panel}>
          {visibleOrders.length ? (
            visibleOrders.map((order) => (
              <div key={order.id}>
                <button
                  type="button"
                  onClick={() =>
                    setOpenOrderId(openOrderId === order.id ? null : order.id)
                  }
                  aria-expanded={openOrderId === order.id}
                  style={styles.orderRow}
                >
                  <div style={{ minWidth: 0, textAlign: "left" }}>
                    <strong>
                      {order.product_name || order.platform_order_id}
                    </strong>
                    <small style={styles.small}>
                      Mã đơn: {order.platform_order_id} ·{" "}
                      {new Date(order.created_at).toLocaleDateString("vi-VN")}
                    </small>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <strong>{money(order.cashback_amount)}</strong>
                    <small style={styles.small}>
                      Giá trị đơn: {money(order.order_amount)}
                    </small>
                  </div>
                  <span
                    style={{
                      ...ui.badge,
                      ...TONE_COLORS[
                        statusTone(CASHBACK_STATUS_META, order.cashback_status)
                      ],
                    }}
                  >
                    {statusLabel(CASHBACK_STATUS_META, order.cashback_status)}
                  </span>
                </button>
                {openOrderId === order.id && (
                  <dl style={styles.detail}>
                    <DetailRow label="Mã đơn sàn" value={order.platform_order_id} />
                    <DetailRow
                      label="Trạng thái đơn"
                      value={statusLabel(ORDER_STATUS_META, order.order_status)}
                    />
                    <DetailRow
                      label="Trạng thái hoàn tiền"
                      value={statusLabel(
                        CASHBACK_STATUS_META,
                        order.cashback_status,
                      )}
                    />
                    <DetailRow
                      label="Giá trị đơn"
                      value={money(order.order_amount)}
                    />
                    <DetailRow
                      label="Tiền hoàn"
                      value={money(order.cashback_amount)}
                    />
                    <DetailRow
                      label="Ghi nhận lúc"
                      value={new Date(order.created_at).toLocaleString("vi-VN")}
                    />
                  </dl>
                )}
              </div>
            ))
          ) : (
            <p style={ui.empty}>Chưa có đơn hàng nào ở trạng thái này.</p>
          )}
        </div>
      </section>

      <section style={{ marginTop: 34 }}>
        <h2 style={{ ...ui.h2, fontSize: 30, marginBottom: 14 }}>
          Lịch sử ví
        </h2>
        <div style={ui.panel}>
          {transactions.length ? (
            transactions.map((tx) => {
              const value = Number(tx.amount || 0);
              return (
                <div key={tx.id} style={ui.row}>
                  <div style={{ minWidth: 0 }}>
                    <strong>
                      {statusLabel(TRANSACTION_TYPE_META, tx.transaction_type)}
                    </strong>
                    <small style={styles.small}>
                      {tx.reference_code} ·{" "}
                      {new Date(tx.created_at).toLocaleString("vi-VN")}
                    </small>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <strong style={{ color: value < 0 ? "#c45142" : "#159366" }}>
                      {value < 0 ? "" : "+"}
                      {money(value)}
                    </strong>
                    <small style={styles.small}>
                      số dư sau: {money(tx.balance_after)}
                    </small>
                  </div>
                  <span
                    style={{
                      ...ui.badge,
                      ...TONE_COLORS[
                        statusTone(TRANSACTION_STATUS_META, tx.status)
                      ],
                    }}
                  >
                    {statusLabel(TRANSACTION_STATUS_META, tx.status)}
                  </span>
                </div>
              );
            })
          ) : (
            <p style={ui.empty}>Ví chưa có giao dịch nào.</p>
          )}
        </div>
      </section>

      <section style={{ marginTop: 34 }}>
        <h2 style={{ ...ui.h2, fontSize: 30, marginBottom: 14 }}>
          Link tracking đã tạo
        </h2>
        <div style={ui.panel}>
          {links.length ? (
            links.map((link) => (
              <div key={link.id} style={ui.row}>
                <div style={{ minWidth: 0 }}>
                  <strong>{link.tracking_id}</strong>
                  <small style={{ ...styles.small, wordBreak: "break-all" }}>
                    {link.affiliate_url || link.normalized_url}
                  </small>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    navigator.clipboard?.writeText(
                      link.affiliate_url || link.normalized_url,
                    )
                  }
                  style={styles.copy}
                >
                  Sao chép
                </button>
              </div>
            ))
          ) : (
            <p style={ui.empty}>Chưa có link tracking nào.</p>
          )}
        </div>
      </section>
    </main>
  );
}

/** Một dòng nhãn – giá trị trong khối chi tiết đơn. */
function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={styles.detailRow}>
      <dt style={styles.detailLabel}>{label}</dt>
      <dd style={styles.detailValue}>{value}</dd>
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  walletGrid: {
    display: "grid",
    gridTemplateColumns: "minmax(300px, 0.85fr) minmax(0, 1.15fr)",
    gap: 18,
    marginTop: 32,
    alignItems: "start",
  },
  walletCard: {
    padding: 24,
    borderRadius: 26,
    background: theme.dark,
    color: theme.onDark,
    boxShadow: "0 32px 90px rgba(114, 72, 8, 0.18)",
  },
  walletHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  live: {
    padding: "7px 10px",
    borderRadius: 10,
    background: "rgba(255, 201, 40, 0.16)",
    color: theme.accent,
    fontSize: 12,
    fontWeight: 800,
  },
  walletAmount: {
    marginTop: 8,
    fontSize: 46,
    lineHeight: 1,
    letterSpacing: "-0.06em",
    fontWeight: 900,
    fontVariantNumeric: "tabular-nums",
  },
  walletRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    marginTop: 24,
    paddingTop: 16,
    borderTop: "1px solid rgba(255,255,255,0.1)",
  },
  walletCta: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 22,
    minHeight: 48,
    borderRadius: 16,
    background:
      "linear-gradient(135deg, rgba(255, 201, 40, 0.96), rgba(255, 160, 48, 0.92))",
    color: theme.ink,
    textDecoration: "none",
    fontWeight: 800,
  },
  generated: {
    marginTop: 12,
    padding: 14,
    borderRadius: 12,
    background: "rgba(255,255,255,.62)",
    color: "#583600",
    wordBreak: "break-all",
  },
  command: {
    margin: 0,
    padding: 12,
    borderRadius: 12,
    background: theme.accentSoft,
    color: theme.ink,
    wordBreak: "break-all",
  },
  sectionHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 14,
    marginBottom: 12,
  },
  filters: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
    padding: 5,
    borderRadius: 999,
    background: "rgba(255,255,255,0.55)",
    border: "1px solid rgba(80, 48, 0, 0.1)",
  },
  filter: {
    border: 0,
    borderRadius: 999,
    padding: "9px 14px",
    background: "transparent",
    color: "#6d5227",
    fontSize: 13,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  filterActive: {
    background: theme.dark,
    color: theme.onDark,
    fontWeight: 800,
  },
  notice: {
    margin: "0 0 14px",
    padding: "11px 14px",
    borderRadius: 14,
    background: "rgba(255, 201, 40, 0.2)",
    color: "#6d4500",
    fontSize: 14,
  },
  detail: {
    display: "grid",
    gap: 8,
    margin: "0 0 16px",
    padding: 16,
    borderRadius: 16,
    background: "rgba(255, 201, 40, 0.16)",
  },
  detailRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 16,
    fontSize: 14,
  },
  detailLabel: { margin: 0, color: theme.inkMuted },
  detailValue: { margin: 0, fontWeight: 700 },
  orderRow: {
    width: "100%",
    border: 0,
    background: "transparent",
    fontFamily: "inherit",
    fontSize: 15,
    color: theme.ink,
    cursor: "pointer",
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.4fr) minmax(0, 1fr) auto",
    alignItems: "center",
    gap: 16,
    padding: "16px 0",
    borderBottom: theme.divider,
  },
  small: {
    display: "block",
    marginTop: 5,
    color: theme.inkMuted,
    fontSize: 13,
  },
  copy: {
    border: "1px solid rgba(80, 48, 0, 0.16)",
    borderRadius: 999,
    padding: "8px 15px",
    background: "rgba(255,255,255,0.6)",
    color: theme.inkSoft,
    fontSize: 13,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
};
