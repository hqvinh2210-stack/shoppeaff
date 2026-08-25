import type { Metadata } from "next";
import AppShell from "./components/app-shell";

export const metadata: Metadata = {
  title: "Bee Hoàn Tiền | Link affiliate Shopee hoàn tiền",
  description:
    "Bee Hoàn Tiền giúp tạo link affiliate Shopee rút gọn, ghi nhận lượt click và hỗ trợ cộng đồng săn deal hoàn tiền.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body style={{ margin: 0 }}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
