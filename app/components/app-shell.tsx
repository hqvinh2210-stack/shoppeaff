"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { theme } from "@/lib/theme";
import { AuthProvider, useAuth } from "./auth-context";
import AuthModal from "./auth-modal";
import TabBar from "./tab-bar";

/**
 * Khung chung của toàn ứng dụng: thanh tab trên cùng + lớp phủ đăng nhập.
 *
 * Nhờ khung này, mọi màn hình dùng chung một nền, một thanh điều hướng và một
 * form đăng nhập duy nhất — không màn hình nào tự dựng lại nữa.
 */
export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ShellInner>{children}</ShellInner>
    </AuthProvider>
  );
}

function ShellInner({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { openAuth, signedIn, ready } = useAuth();

  // /login và /register là lối vào sâu (bookmark, link cũ) của cùng lớp phủ.
  // Trang bên dưới vẫn là trang chủ nên người dùng không bao giờ thấy màn trắng.
  useEffect(() => {
    if (pathname !== "/login" && pathname !== "/register") return;
    if (!ready) return;
    // Đã đăng nhập rồi thì không bắt đăng nhập lại, chỉ đưa về trang chủ.
    if (signedIn) {
      router.replace("/");
      return;
    }
    openAuth(pathname === "/register" ? "register" : "login");
  }, [pathname, ready, signedIn, openAuth, router]);

  return (
    <div
      style={{
        minHeight: "100dvh",
        fontFamily: theme.font,
        color: theme.ink,
        background: theme.pageBackground,
      }}
    >
      <TabBar />
      {children}
      <AuthModal />
    </div>
  );
}
