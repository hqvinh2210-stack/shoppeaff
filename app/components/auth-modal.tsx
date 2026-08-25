"use client";

import Script from "next/script";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { apiFetch, errorMessage } from "@/lib/api";
import { theme } from "@/lib/theme";
import { useAuth } from "./auth-context";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement,
            options: Record<string, string | number>,
          ) => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

/**
 * Form đăng nhập/đăng ký dạng lớp phủ.
 *
 * Cố tình KHÔNG phải một trang riêng: người dùng luôn nhìn thấy trang chủ (hoặc
 * màn hình đang xem) ở phía sau, đóng lớp phủ là quay lại đúng chỗ cũ.
 */
export default function AuthModal() {
  const { authOpen, authMode, setAuthMode, closeAuth, signIn } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const [identifier, setIdentifier] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleReady, setGoogleReady] = useState(false);
  const googleButton = useRef<HTMLDivElement>(null);

  const register = authMode === "register";

  function dismiss() {
    setError("");
    closeAuth();
    // /login và /register chỉ là lối vào sâu của cùng lớp phủ này. Đóng lại thì
    // đưa URL về trang chủ để không kẹt ở một route rỗng.
    if (pathname === "/login" || pathname === "/register") router.replace("/");
  }

  async function finish(tokens: { access_token: string; refresh_token: string }) {
    await signIn(tokens.access_token, tokens.refresh_token);
    setPassword("");
    setError("");
    if (pathname === "/login" || pathname === "/register") router.replace("/");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = register
        ? {
            email: email || undefined,
            phone: phone || undefined,
            full_name: fullName || undefined,
            password,
          }
        : { identifier, password };
      const result = await apiFetch<{ access_token: string; refresh_token: string }>(
        register ? "/auth/register" : "/auth/login",
        { method: "POST", body },
      );
      await finish(result);
    } catch (submitError) {
      setError(errorMessage(submitError, "Không thể xác thực tài khoản"));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!authOpen || !googleReady || !GOOGLE_CLIENT_ID || !googleButton.current)
      return;
    googleButton.current.replaceChildren();
    window.google?.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response) => {
        void (async () => {
          try {
            const result = await apiFetch<{ access_token: string; refresh_token: string }>(
              "/auth/google",
              { method: "POST", body: { id_token: response.credential } },
            );
            await finish(result);
          } catch (googleError) {
            setError(errorMessage(googleError, "Đăng nhập Google thất bại"));
          }
        })();
      },
    });
    window.google?.accounts.id.renderButton(googleButton.current, {
      theme: "outline",
      size: "large",
      width: 420,
    });
    // finish/pathname đổi theo mỗi lần render nhưng không ảnh hưởng tới việc
    // dựng nút Google, nên chỉ theo dõi các điều kiện hiển thị.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authOpen, googleReady]);

  useEffect(() => {
    if (!authOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") dismiss();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authOpen, pathname]);

  if (!authOpen) return null;

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => setGoogleReady(true)}
      />
      <div
        style={styles.scrim}
        onClick={(event) => {
          if (event.target === event.currentTarget) dismiss();
        }}
      >
        <section
          role="dialog"
          aria-modal="true"
          aria-label={register ? "Đăng ký tài khoản" : "Đăng nhập"}
          style={styles.card}
        >
          <div style={styles.cardHead}>
            <strong style={{ fontSize: 22, letterSpacing: "-0.03em" }}>
              🐝 Bee Hoàn Tiền
            </strong>
            <button
              type="button"
              onClick={dismiss}
              aria-label="Đóng"
              style={styles.close}
            >
              ×
            </button>
          </div>

          <div style={styles.tabs}>
            <button
              type="button"
              onClick={() => setAuthMode("login")}
              style={{ ...styles.tab, ...(register ? {} : styles.tabActive) }}
            >
              Đăng nhập
            </button>
            <button
              type="button"
              onClick={() => setAuthMode("register")}
              style={{ ...styles.tab, ...(register ? styles.tabActive : {}) }}
            >
              Đăng ký
            </button>
          </div>

          {GOOGLE_CLIENT_ID ? (
            <div ref={googleButton} style={{ minHeight: 44, marginBottom: 16 }} />
          ) : (
            <p style={styles.notice}>
              Đăng nhập Google chưa khả dụng — thiếu
              <code> NEXT_PUBLIC_GOOGLE_CLIENT_ID</code>.
            </p>
          )}

          <form onSubmit={submit} style={{ display: "grid", gap: 14 }}>
            {register ? (
              <>
                <label style={styles.label}>
                  Họ tên
                  <input
                    style={styles.input}
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Nguyễn Văn A"
                  />
                </label>
                <label style={styles.label}>
                  Email
                  <input
                    style={styles.input}
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                  />
                </label>
                <label style={styles.label}>
                  Số điện thoại
                  <input
                    style={styles.input}
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="096..."
                  />
                </label>
                <p style={styles.hint}>
                  Cần ít nhất một trong hai: email hoặc số điện thoại.
                </p>
              </>
            ) : (
              <label style={styles.label}>
                Email hoặc số điện thoại
                <input
                  style={styles.input}
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  required
                  placeholder="you@example.com"
                />
              </label>
            )}

            <label style={styles.label}>
              Mật khẩu
              <input
                style={styles.input}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
                placeholder="Tối thiểu 8 ký tự"
              />
            </label>

            {error && <p style={styles.error}>{error}</p>}

            <button type="submit" disabled={busy} style={styles.submit}>
              {busy
                ? "Đang xử lý..."
                : register
                  ? "Tạo tài khoản"
                  : "Đăng nhập"}
            </button>
          </form>
        </section>
      </div>
    </>
  );
}

const styles: Record<string, CSSProperties> = {
  scrim: {
    position: "fixed",
    inset: 0,
    zIndex: 40,
    display: "grid",
    placeItems: "center",
    padding: 20,
    background: "rgba(36, 22, 7, 0.42)",
    backdropFilter: "blur(3px)",
  },
  card: {
    width: "min(520px, 100%)",
    maxHeight: "88dvh",
    overflow: "auto",
    padding: 28,
    borderRadius: 26,
    background: theme.surfaceSolid,
    color: theme.ink,
    fontFamily: theme.font,
    boxShadow: "0 32px 90px rgba(36, 22, 7, 0.34)",
  },
  cardHead: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  },
  close: {
    border: 0,
    background: "transparent",
    fontSize: 26,
    lineHeight: 1,
    color: theme.inkFaint,
    cursor: "pointer",
  },
  tabs: {
    display: "flex",
    gap: 22,
    marginBottom: 20,
    borderBottom: "1px solid #eadab8",
  },
  tab: {
    border: 0,
    background: "none",
    padding: "0 0 12px",
    color: theme.inkFaint,
    fontWeight: 700,
    fontSize: 15,
    cursor: "pointer",
  },
  tabActive: {
    // Dùng inset box-shadow thay cho `borderBottom`: trộn `border` rút gọn với
    // `borderBottom` giữa hai lần render làm React cảnh báo xung đột thuộc tính.
    boxShadow: `inset 0 -2px 0 ${theme.accentLine}`,
    color: theme.ink,
    fontWeight: 800,
  },
  label: {
    display: "grid",
    gap: 7,
    fontWeight: 700,
    fontSize: 14,
    color: theme.inkSoft,
  },
  input: {
    padding: "12px 14px",
    border: "1px solid #d8c6a7",
    borderRadius: 12,
    background: "#fffdf8",
    color: theme.ink,
    fontSize: 15,
    fontFamily: "inherit",
  },
  hint: {
    margin: 0,
    color: theme.inkFaint,
    fontSize: 13,
  },
  notice: {
    margin: "0 0 16px",
    padding: "10px 12px",
    borderRadius: 12,
    background: "#f4e9d3",
    color: theme.inkFaint,
    fontSize: 13,
  },
  error: {
    margin: 0,
    color: theme.danger,
    fontWeight: 700,
  },
  submit: {
    width: "100%",
    border: 0,
    borderRadius: 14,
    padding: "14px 16px",
    background: theme.dark,
    color: theme.onDark,
    fontWeight: 800,
    fontSize: 15,
    cursor: "pointer",
  },
};
