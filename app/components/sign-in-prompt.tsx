"use client";

import { theme, ui } from "@/lib/theme";
import { useAuth } from "./auth-context";

/**
 * Khối thay thế nội dung khi khách mở một tab cần đăng nhập.
 *
 * Cố tình không redirect: thanh tab vẫn ở nguyên vị trí, người dùng bấm "Trang
 * chủ" là quay lại ngay, hoặc đăng nhập tại chỗ bằng lớp phủ.
 */
export default function SignInPrompt({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  const { openAuth } = useAuth();

  return (
    <main style={ui.shell}>
      <p style={ui.kicker}>Cần đăng nhập</p>
      <h1 style={ui.h1}>{title}</h1>
      <p style={{ ...ui.lead, maxWidth: 620 }}>{text}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 28 }}>
        <button
          type="button"
          onClick={() => openAuth("login")}
          style={ui.btnPrimary}
        >
          Đăng nhập
        </button>
        <button
          type="button"
          onClick={() => openAuth("register")}
          style={ui.btnGhost}
        >
          Tạo tài khoản mới
        </button>
      </div>
      <p style={{ marginTop: 22, color: theme.inkMuted, fontSize: 14 }}>
        Bạn vẫn có thể quay lại tab <strong>Trang chủ</strong> bất cứ lúc nào.
      </p>
    </main>
  );
}
