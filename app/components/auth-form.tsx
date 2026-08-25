"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import SiteHeader from "./site-header";
import { API_BASE as API, bypassHeaders } from "../../lib/api";

export default function AuthForm({ register = false }: { register?: boolean }) {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const body = register ? { email: email || undefined, phone: phone || undefined, full_name: fullName || undefined, password } : { identifier, password };
      if (!API) throw new Error("Frontend chưa được cấu hình địa chỉ API. Hãy đặt NEXT_PUBLIC_API_URL trong phần Environment Variables.");
      const response = await fetch(`${API}/auth/${register ? "register" : "login"}`, { method: "POST", headers: { "Content-Type": "application/json", ...bypassHeaders }, body: JSON.stringify(body) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Không thể xác thực tài khoản");
      localStorage.setItem("cashback_access_token", data.access_token);
      localStorage.setItem("cashback_refresh_token", data.refresh_token);
      window.location.href = "/dashboard";
    } catch (submitError) { setError(submitError instanceof TypeError ? "Không kết nối được máy chủ API. Kiểm tra NEXT_PUBLIC_API_URL và CORS_ORIGINS." : submitError instanceof Error ? submitError.message : "Không thể xác thực tài khoản"); }
    finally { setBusy(false); }
  }

  return <main style={styles.page}><SiteHeader /><section style={styles.layout}><div><p style={styles.kicker}>BEE HOÀN TIỀN</p><h1 style={styles.title}>{register ? "Tạo tài khoản để bắt đầu nhận hoàn tiền." : "Đăng nhập để quản lý tiền hoàn."}</h1><p style={styles.lead}>Mỗi tài khoản có tracking riêng, ví riêng và lịch sử đơn hàng riêng.</p></div><form onSubmit={submit} style={styles.form}><div style={styles.tabs}><a href="/login" style={!register ? styles.activeTab : styles.tab}>Đăng nhập</a><a href="/register" style={register ? styles.activeTab : styles.tab}>Đăng ký</a></div>{register ? <><label>Họ tên<input value={fullName} onChange={event => setFullName(event.target.value)} placeholder="Nguyễn Văn A" /></label><label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Số điện thoại<input value={phone} onChange={event => setPhone(event.target.value)} placeholder="096..." /></label></> : <label>Email hoặc số điện thoại<input value={identifier} onChange={event => setIdentifier(event.target.value)} required placeholder="you@example.com" /> </label>}<label>Mật khẩu<input type="password" value={password} onChange={event => setPassword(event.target.value)} minLength={8} required placeholder="Tối thiểu 8 ký tự" /></label>{error && <p style={styles.error}>{error}</p>}<button disabled={busy} style={styles.submit}>{busy ? "Đang xử lý..." : register ? "Tạo tài khoản" : "Đăng nhập"}</button></form></section></main>;
}

const styles: Record<string, React.CSSProperties> = { page: { minHeight: "100dvh", padding: "24px max(24px, calc((100% - 1120px) / 2))", background: "linear-gradient(135deg,#fff7df,#f5e6f0)", color: "#241607" }, header: { display: "flex", justifyContent: "space-between", alignItems: "center" }, brand: { display: "flex", alignItems: "center", gap: 10, color: "#241607", textDecoration: "none", fontWeight: 800, fontSize: 20 }, logo: { display: "grid", placeItems: "center", width: 42, height: 42, borderRadius: 13, background: "#ffc928", fontWeight: 900, fontSize: 22 }, back: { color: "#62451c", textDecoration: "none", fontWeight: 700 }, layout: { display: "grid", gridTemplateColumns: "1fr 430px", gap: 70, alignItems: "center", minHeight: "calc(100dvh - 90px)" }, kicker: { color: "#9b6a00", fontWeight: 900, letterSpacing: ".12em", fontSize: 12 }, title: { fontSize: "clamp(44px,7vw,82px)", lineHeight: .95, letterSpacing: "-.06em", margin: "18px 0" }, lead: { color: "#62451c", fontSize: 18, lineHeight: 1.6 }, form: { display: "grid", gap: 16, padding: 30, borderRadius: 22, background: "rgba(255,255,255,.76)", boxShadow: "0 25px 70px rgba(83,44,0,.15)" }, tabs: { display: "flex", gap: 24, borderBottom: "1px solid #eadab8", marginBottom: 6 }, tab: { color: "#876d43", textDecoration: "none", paddingBottom: 13, fontWeight: 700 }, activeTab: { color: "#241607", textDecoration: "none", paddingBottom: 13, fontWeight: 800, borderBottom: "2px solid #c98200" }, input: { display: "block", width: "100%", boxSizing: "border-box", marginTop: 7, padding: "13px 14px", border: "1px solid #dac9aa", borderRadius: 10, background: "#fffdf8", fontSize: 15 }, submit: { border: 0, borderRadius: 10, padding: "14px 18px", background: "#241607", color: "#fff7df", fontWeight: 800, cursor: "pointer" }, error: { color: "#b42318", margin: 0 } };
