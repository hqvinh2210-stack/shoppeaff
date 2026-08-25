"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { CSSProperties } from "react";
import { theme } from "@/lib/theme";
import { useAuth } from "./auth-context";

type Tab = {
  href: string;
  label: string;
  /** Tab cần đăng nhập: khách bấm vào sẽ mở lớp phủ đăng nhập tại chỗ. */
  auth?: boolean;
  /** Tab chỉ dành cho quản trị. */
  admin?: boolean;
};

const TABS: Tab[] = [
  { href: "/", label: "Trang chủ" },
  { href: "/dashboard", label: "Tổng quan", auth: true },
  { href: "/withdrawals", label: "Rút tiền", auth: true },
  { href: "/admin", label: "Báo cáo", auth: true, admin: true },
];

/**
 * Thanh tab cố định trên cùng, dùng chung cho mọi màn hình.
 *
 * Khách chưa đăng nhập vẫn thấy đủ các tab: bấm vào tab cần quyền sẽ bật lớp
 * phủ đăng nhập ngay trên trang đang xem thay vì chuyển sang một trang trắng.
 */
export default function TabBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { signedIn, account, isAdmin, openAuth, signOut } = useAuth();

  // Backend chưa trả `role` (điểm B5) nên khi thiếu thông tin, tab quản trị vẫn
  // hiển thị cho người đã đăng nhập và để backend chặn bằng 403.
  const roleKnown = Boolean(account?.role);
  const visibleTabs = TABS.filter(
    (tab) => !tab.admin || !signedIn || !roleKnown || isAdmin,
  );

  function activeFor(href: string): boolean {
    if (href === "/") return pathname === "/" || pathname === "/login" || pathname === "/register";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  function go(tab: Tab) {
    if (tab.auth && !signedIn) {
      openAuth("login");
      return;
    }
    router.push(tab.href);
  }

  return (
    <header style={styles.header}>
      <div style={styles.inner}>
        <Link href="/" style={styles.brand} aria-label="Bee Hoàn Tiền — trang chủ">
          <span aria-hidden="true" style={styles.logo}>
            🐝
          </span>
          <strong style={styles.brandName}>Bee Hoàn Tiền</strong>
        </Link>

        <nav aria-label="Chuyển tính năng" style={styles.tabs}>
          {visibleTabs.map((tab) => {
            const active = activeFor(tab.href);
            return (
              <button
                key={tab.href}
                type="button"
                onClick={() => go(tab)}
                aria-current={active ? "page" : undefined}
                style={{ ...styles.tab, ...(active ? styles.tabActive : {}) }}
              >
                {tab.label}
                {tab.auth && !signedIn && (
                  <span aria-hidden="true" style={styles.lock}>
                    🔒
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div style={styles.actions}>
          {signedIn ? (
            <>
              <span style={styles.who} title={account?.email ?? undefined}>
                {account?.full_name || account?.email || account?.user_code}
              </span>
              <button
                type="button"
                onClick={() => {
                  signOut();
                  router.push("/");
                }}
                style={styles.ghost}
              >
                Đăng xuất
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => openAuth("login")}
                style={styles.ghost}
              >
                Đăng nhập
              </button>
              <button
                type="button"
                onClick={() => openAuth("register")}
                style={styles.solid}
              >
                Đăng ký
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

const styles: Record<string, CSSProperties> = {
  header: {
    position: "sticky",
    top: 0,
    zIndex: 20,
    background: "rgba(255, 250, 240, 0.78)",
    backdropFilter: "blur(16px)",
    borderBottom: "1px solid rgba(80, 48, 0, 0.1)",
    fontFamily: theme.font,
    color: theme.ink,
  },
  inner: {
    maxWidth: theme.maxWidth,
    margin: "0 auto",
    padding: "14px 24px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 18,
    flexWrap: "wrap",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 11,
    color: theme.ink,
    textDecoration: "none",
  },
  logo: {
    width: 40,
    height: 40,
    borderRadius: 14,
    display: "grid",
    placeItems: "center",
    background: theme.accent,
    boxShadow: "0 14px 30px rgba(120, 72, 0, 0.18)",
    fontSize: 21,
  },
  brandName: {
    fontSize: 19,
    letterSpacing: "-0.03em",
  },
  tabs: {
    display: "flex",
    alignItems: "center",
    gap: 4,
    padding: 5,
    borderRadius: 999,
    background: "rgba(255, 255, 255, 0.55)",
    border: "1px solid rgba(80, 48, 0, 0.1)",
  },
  tab: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
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
    boxShadow: "0 12px 26px rgba(36, 22, 7, 0.22)",
  },
  lock: {
    fontSize: 10,
    opacity: 0.65,
  },
  actions: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  who: {
    maxWidth: 180,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: theme.inkSoft,
    fontSize: 14,
    fontWeight: 700,
  },
  ghost: {
    borderRadius: 999,
    padding: "10px 17px",
    border: "1px solid rgba(70, 43, 8, 0.18)",
    background: "rgba(255, 255, 255, 0.46)",
    color: "#3b2508",
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
  solid: {
    borderRadius: 999,
    padding: "10px 17px",
    border: `1px solid ${theme.dark}`,
    background: theme.dark,
    color: theme.onDark,
    fontSize: 14,
    fontWeight: 700,
    fontFamily: "inherit",
    cursor: "pointer",
  },
};
