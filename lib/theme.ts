import type { CSSProperties } from "react";

/**
 * Design tokens của Bee Hoàn Tiền, trích nguyên từ trang chủ (`app/page.tsx`).
 *
 * Mọi màn hình tính năng (tổng quan, rút tiền, báo cáo) đều dùng chung file này
 * để giữ đúng một ngôn ngữ thiết kế: nền vàng kem, chữ nâu đậm, panel kính mờ,
 * điểm nhấn vàng mật ong.
 */
export const theme = {
  /* Chữ */
  ink: "#241607",
  inkSoft: "#62451c",
  inkMuted: "#745729",
  inkFaint: "#876d43",
  onDark: "#fff7df",
  onDarkSoft: "#d5c2a1",

  /* Điểm nhấn */
  accent: "#ffc928",
  accentDeep: "#9b6a00",
  accentLine: "#c98200",
  accentSoft: "#f7df9d",

  /* Bề mặt */
  surface: "rgba(255, 255, 255, 0.54)",
  surfaceStrong: "rgba(255, 255, 255, 0.72)",
  surfaceSolid: "#fffaf0",
  dark: "#241607",

  /* Viền */
  border: "1px solid rgba(91, 59, 8, 0.12)",
  borderStrong: "1px solid rgba(80, 48, 0, 0.2)",
  divider: "1px solid rgba(80, 48, 0, 0.12)",

  /* Nền trang */
  pageBackground:
    "radial-gradient(circle at 15% 12%, rgba(255, 197, 66, 0.36), transparent 32%), radial-gradient(circle at 82% 6%, rgba(255, 136, 55, 0.22), transparent 28%), linear-gradient(135deg, #fff7df 0%, #fffaf0 48%, #f7df9d 100%)",

  font: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  maxWidth: 1180,
  danger: "#b42318",
} as const;

/** Các khối style dùng lại được trên mọi màn hình tính năng. */
export const ui: Record<string, CSSProperties> = {
  /** Bọc ngoài cùng của một trang tính năng. */
  page: {
    minHeight: "100dvh",
    fontFamily: theme.font,
    color: theme.ink,
    background: theme.pageBackground,
  },

  /** Khung nội dung căn giữa, cùng bề rộng với trang chủ. */
  shell: {
    maxWidth: theme.maxWidth,
    margin: "0 auto",
    padding: "38px 24px 86px",
  },

  /** Dòng chữ nhỏ in hoa phía trên tiêu đề. */
  kicker: {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    margin: "0 0 18px",
    padding: "8px 12px",
    borderRadius: 12,
    background: "rgba(255, 201, 40, 0.24)",
    color: "#6d4500",
    fontSize: 13,
    fontWeight: 800,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },

  h1: {
    margin: 0,
    fontSize: "clamp(34px, 5vw, 62px)",
    lineHeight: 0.96,
    letterSpacing: "-0.06em",
    textWrap: "balance",
  },

  h2: {
    margin: 0,
    fontSize: 23,
    letterSpacing: "-0.035em",
  },

  lead: {
    margin: "20px 0 0",
    color: theme.inkSoft,
    fontSize: 18,
    lineHeight: 1.7,
    textWrap: "pretty",
  },

  /** Panel kính mờ — khối nội dung mặc định. */
  panel: {
    padding: 24,
    borderRadius: 26,
    background: theme.surface,
    border: theme.border,
  },

  /** Panel nâu đậm — dùng cho khối số liệu nổi bật. */
  panelDark: {
    padding: 24,
    borderRadius: 26,
    background: theme.dark,
    color: theme.onDark,
  },

  /** Ô số liệu nhỏ trên nền vàng nhạt. */
  metric: {
    display: "grid",
    gap: 6,
    padding: 18,
    borderRadius: 18,
    background: "rgba(255,255,255,0.5)",
  },

  btnPrimary: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 50,
    padding: "0 22px",
    border: 0,
    borderRadius: 16,
    background: theme.dark,
    color: theme.onDark,
    fontWeight: 800,
    cursor: "pointer",
    boxShadow: "0 18px 38px rgba(36, 22, 7, 0.2)",
  },

  btnAccent: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 50,
    padding: "0 20px",
    border: 0,
    borderRadius: 16,
    background: theme.accent,
    color: theme.ink,
    fontWeight: 800,
    cursor: "pointer",
  },

  btnGhost: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 50,
    padding: "0 20px",
    borderRadius: 16,
    background: "rgba(255,255,255,0.55)",
    border: "1px solid rgba(80, 48, 0, 0.14)",
    color: "#2d1a04",
    fontWeight: 800,
    cursor: "pointer",
    textDecoration: "none",
  },

  field: {
    display: "grid",
    gap: 8,
    color: theme.inkSoft,
    fontWeight: 800,
    fontSize: 14,
  },

  input: {
    minHeight: 50,
    padding: "0 15px",
    border: theme.borderStrong,
    borderRadius: 12,
    background: theme.surfaceStrong,
    color: theme.ink,
    fontSize: 15,
    fontFamily: "inherit",
  },

  badge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 12px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 800,
    whiteSpace: "nowrap",
  },

  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 16,
    padding: "14px 0",
    borderBottom: theme.divider,
  },

  empty: {
    margin: 0,
    padding: "26px 0",
    color: theme.inkMuted,
    textAlign: "center",
  },

  error: {
    margin: "10px 0 0",
    color: theme.danger,
    fontWeight: 700,
  },
};
