"use client";

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { errorMessage } from "@/lib/api";
import { theme, ui } from "@/lib/theme";
import { useAuth } from "./auth-context";

type ZaloStatus = { linked: boolean; zalo_user_id?: string | null };
type LinkToken = { token: string; expires_at: string; command?: string };

/** Đếm ngược tới lúc token liên kết hết hạn (TTL 15 phút ở backend). */
function useCountdown(expiresAt: string | undefined): string {
  const [label, setLabel] = useState("");
  useEffect(() => {
    if (!expiresAt) return;
    const tick = () => {
      const left = new Date(expiresAt).getTime() - Date.now();
      if (left <= 0) {
        setLabel("đã hết hạn");
        return;
      }
      const minutes = Math.floor(left / 60000);
      const seconds = Math.floor((left % 60000) / 1000);
      setLabel(`còn ${minutes}:${String(seconds).padStart(2, "0")}`);
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);
  return label;
}

/**
 * Liên kết tài khoản web với bot Telegram / Zalo.
 *
 * Backend đã có sẵn các endpoint này từ lâu nhưng chưa có màn hình nào gọi tới
 * (điểm G1 trong tài liệu đặc tả).
 */
export default function ChannelLinks() {
  const { request } = useAuth();
  const [zalo, setZalo] = useState<ZaloStatus | null>(null);
  const [zaloToken, setZaloToken] = useState<LinkToken | null>(null);
  const [telegramToken, setTelegramToken] = useState<LinkToken | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const zaloCountdown = useCountdown(zaloToken?.expires_at);
  const telegramCountdown = useCountdown(telegramToken?.expires_at);

  const loadZalo = useCallback(async () => {
    try {
      setZalo(await request<ZaloStatus>("/zalo/status"));
    } catch (caught) {
      setError(errorMessage(caught, "Không đọc được trạng thái Zalo"));
    }
  }, [request]);

  useEffect(() => {
    void loadZalo();
  }, [loadZalo]);

  async function createZaloToken() {
    setError("");
    setMessage("");
    try {
      setZaloToken(await request<LinkToken>("/zalo/link", { method: "POST" }));
    } catch (caught) {
      setError(errorMessage(caught, "Không tạo được mã liên kết Zalo"));
    }
  }

  async function unlinkZalo() {
    if (!window.confirm("Ngắt liên kết Zalo? Bot sẽ không ghi nhận đơn về tài khoản này nữa.")) return;
    setError("");
    try {
      await request("/zalo/unlink", { method: "DELETE" });
      setMessage("Đã ngắt liên kết Zalo.");
      setZaloToken(null);
      await loadZalo();
    } catch (caught) {
      setError(errorMessage(caught, "Không ngắt được liên kết"));
    }
  }

  async function createTelegramToken() {
    setError("");
    setMessage("");
    try {
      setTelegramToken(
        await request<LinkToken>("/telegram/link", { method: "POST" }),
      );
    } catch (caught) {
      setError(errorMessage(caught, "Không tạo được mã liên kết Telegram"));
    }
  }

  function copy(value: string) {
    navigator.clipboard?.writeText(value);
    setMessage("Đã sao chép vào clipboard.");
  }

  return (
    <section style={{ ...ui.panel, display: "grid", gap: 16 }}>
      <div>
        <h2 style={ui.h2}>Nhận link ngay trong chat</h2>
        <p style={styles.lead}>
          Liên kết một lần, sau đó gửi link Shopee thẳng cho bot — đơn vẫn ghi
          nhận về đúng tài khoản này.
        </p>
      </div>

      <div style={styles.grid}>
        {/* --------------------------------- Telegram --------------------------------- */}
        <div style={styles.card}>
          <div style={styles.cardHead}>
            <strong>Telegram</strong>
          </div>
          <button
            type="button"
            onClick={createTelegramToken}
            style={{ ...ui.btnGhost, minHeight: 44 }}
          >
            Tạo mã liên kết
          </button>
          {telegramToken && (
            <div style={styles.tokenBox}>
              <code style={styles.code}>{telegramToken.command}</code>
              <div style={styles.tokenFoot}>
                <span>Gửi lệnh này cho bot · {telegramCountdown}</span>
                <button
                  type="button"
                  onClick={() => copy(telegramToken.command ?? telegramToken.token)}
                  style={styles.copy}
                >
                  Sao chép
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ----------------------------------- Zalo ----------------------------------- */}
        <div style={styles.card}>
          <div style={styles.cardHead}>
            <strong>Zalo</strong>
            {zalo && (
              <span
                style={{
                  ...ui.badge,
                  ...(zalo.linked
                    ? { color: "#159366", background: "#e4f7ed" }
                    : { color: theme.inkMuted, background: "#f1f3f7" }),
                }}
              >
                {zalo.linked ? "Đã liên kết" : "Chưa liên kết"}
              </span>
            )}
          </div>

          {zalo?.linked ? (
            <>
              <p style={styles.lead}>
                Zalo ID: <strong>{zalo.zalo_user_id}</strong>
              </p>
              <button
                type="button"
                onClick={unlinkZalo}
                style={{ ...ui.btnGhost, minHeight: 44 }}
              >
                Ngắt liên kết
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={createZaloToken}
                style={{ ...ui.btnGhost, minHeight: 44 }}
              >
                Tạo mã liên kết
              </button>
              {zaloToken && (
                <div style={styles.tokenBox}>
                  <code style={styles.code}>{zaloToken.token}</code>
                  <div style={styles.tokenFoot}>
                    <span>Gửi mã này cho bot Zalo · {zaloCountdown}</span>
                    <button
                      type="button"
                      onClick={() => copy(zaloToken.token)}
                      style={styles.copy}
                    >
                      Sao chép
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {message && <p style={styles.success}>{message}</p>}
      {error && <p style={ui.error}>{error}</p>}
    </section>
  );
}

const styles: Record<string, CSSProperties> = {
  lead: { margin: "6px 0 0", color: theme.inkSoft, fontSize: 14, lineHeight: 1.6 },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: 12,
  },
  card: {
    display: "grid",
    gap: 10,
    alignContent: "start",
    padding: 16,
    borderRadius: 18,
    background: "rgba(255,255,255,0.55)",
    border: "1px solid rgba(80, 48, 0, 0.12)",
  },
  cardHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
  },
  tokenBox: {
    display: "grid",
    gap: 8,
    padding: 12,
    borderRadius: 14,
    background: theme.accentSoft,
  },
  code: {
    display: "block",
    wordBreak: "break-all",
    fontSize: 13,
    fontWeight: 700,
    color: theme.ink,
  },
  tokenFoot: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    color: "#6d4500",
    fontSize: 12,
  },
  copy: {
    border: "1px solid rgba(80, 48, 0, 0.2)",
    borderRadius: 999,
    padding: "6px 12px",
    background: "rgba(255,255,255,0.7)",
    color: theme.inkSoft,
    fontSize: 12,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  success: { margin: 0, color: "#159366", fontWeight: 700 },
};
