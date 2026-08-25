"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Trang chủ" },
  { href: "/dashboard", label: "Tổng quan" },
  { href: "/withdrawals", label: "Rút tiền" },
];

export default function SiteHeader() {
  const pathname = usePathname();
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    setSignedIn(Boolean(localStorage.getItem("cashback_access_token")));
  }, [pathname]);

  function logout() {
    localStorage.removeItem("cashback_access_token");
    window.location.href = "/";
  }

  return (
    <header style={styles.header}>
      <Link href="/" style={styles.brand} aria-label="Bee Hoàn Tiền - Trang chủ">
        <span style={styles.logo}>B</span>
        <strong>Bee Hoàn Tiền</strong>
      </Link>
      <nav aria-label="Điều hướng chính" style={styles.nav}>
        {navItems.map(item => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={pathname === item.href ? "page" : undefined}
            style={{ ...styles.link, ...(pathname === item.href ? styles.active : {}) }}
          >
            {item.label}
          </Link>
        ))}
        {signedIn ? (
          <button type="button" onClick={logout} style={styles.logout}>Đăng xuất</button>
        ) : (
          <>
            <Link href="/login" style={styles.login}>Đăng nhập</Link>
            <Link href="/register" style={styles.register}>Đăng ký</Link>
          </>
        )}
      </nav>
    </header>
  );
}

const styles = {
  header: {
    minHeight: 76,
    boxSizing: "border-box" as const,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 20,
    padding: "14px max(20px, calc((100% - 1480px) / 2))",
    background: "rgba(255, 253, 248, .9)",
    borderBottom: "1px solid rgba(230, 222, 208, .9)",
    backdropFilter: "blur(16px)",
    position: "sticky" as const,
    top: 0,
    zIndex: 10,
  },
  brand: { display: "flex", alignItems: "center", gap: 10, color: "#2a241b", textDecoration: "none", fontSize: 20 },
  logo: { display: "grid", placeItems: "center", width: 40, height: 40, borderRadius: 12, background: "#f8b900", color: "#2a241b", fontWeight: 900, fontSize: 21 },
  nav: { display: "flex", alignItems: "center", justifyContent: "flex-end", flexWrap: "wrap" as const, gap: 6, fontSize: 14 },
  link: { color: "#687386", textDecoration: "none", padding: "10px 12px", borderRadius: 8 },
  active: { color: "#a86600", background: "#fff3c9", fontWeight: 800 },
  login: { color: "#5f6877", textDecoration: "none", padding: "10px 12px", fontWeight: 700 },
  register: { color: "#fffdf8", textDecoration: "none", padding: "10px 14px", borderRadius: 8, background: "#2a241b", fontWeight: 800 },
  logout: { border: "1px solid #d9cdbc", borderRadius: 8, padding: "9px 12px", background: "transparent", color: "#5f6877", fontWeight: 700, cursor: "pointer" },
};
