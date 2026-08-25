"use client";

import { useState, type FormEvent } from "react";
import { errorMessage } from "@/lib/api";
import { useAuth } from "./components/auth-context";

const steps = [
  {
    label: "01",
    title: "Gửi link sản phẩm",
    text: "Dán link Shopee vào bot Telegram hoặc Zalo. Bee Hoàn Tiền tự nhận diện và xử lý link.",
  },
  {
    label: "02",
    title: "Nhận link hoàn tiền",
    text: "Hệ thống tạo link rút gọn theo mã riêng, dễ chia sẻ và theo dõi lượt click.",
  },
  {
    label: "03",
    title: "Theo dõi chuyển đổi",
    text: "Mỗi lượt truy cập được ghi nhận để bạn kiểm tra hiệu quả chiến dịch affiliate.",
  },
];

const stats = [
  ["24/7", "bot hoạt động"],
  ["1 chạm", "tạo link nhanh"],
  ["0đ", "chi phí dùng thử"],
];

type GeneratedLink = { tracking_id: string; affiliate_url?: string };

export default function HomePage() {
  const { signedIn, openAuth, request } = useAuth();
  const [sourceUrl, setSourceUrl] = useState("");
  const [convertedLink, setConvertedLink] = useState<GeneratedLink | null>(null);
  const [converting, setConverting] = useState(false);
  const [error, setError] = useState("");

  async function convertLink(event: FormEvent) {
    event.preventDefault();
    if (!signedIn) {
      setError("Vui lòng đăng nhập để tạo link tracking riêng.");
      openAuth("login");
      return;
    }
    setConverting(true);
    setError("");
    setConvertedLink(null);
    try {
      const link = await request<GeneratedLink>("/affiliate/generate-link", {
        method: "POST",
        body: { original_url: sourceUrl },
      });
      setConvertedLink(link);
      setSourceUrl("");
    } catch (convertError) {
      setError(errorMessage(convertError, "Không thể chuyển đổi link"));
    } finally {
      setConverting(false);
    }
  }

  return (
    <main>
      <section
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "52px 24px 86px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1.08fr) minmax(320px, 0.92fr)",
            gap: 38,
            alignItems: "center",
          }}
        >
          <div>
            <p
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                margin: "0 0 22px",
                padding: "8px 12px",
                borderRadius: 12,
                background: "rgba(255, 201, 40, 0.24)",
                color: "#6d4500",
                fontSize: 13,
                fontWeight: 800,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              Cashback affiliate assistant
            </p>

            <h1
              style={{
                margin: 0,
                maxWidth: 760,
                fontSize: "clamp(46px, 8vw, 104px)",
                lineHeight: 0.9,
                letterSpacing: "-0.075em",
                textWrap: "balance",
              }}
            >
              Săn deal Shopee, hoàn tiền mê ly.
            </h1>

            <p
              style={{
                maxWidth: 620,
                margin: "28px 0 0",
                color: "#62451c",
                fontSize: 19,
                lineHeight: 1.7,
                textWrap: "pretty",
              }}
            >
              Bee Hoàn Tiền biến link sản phẩm thành link affiliate ngắn, đẹp và
              có ghi nhận lượt click. Phù hợp cho cộng đồng săn sale, nhóm deal
              và người làm tiếp thị liên kết.
            </p>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 14,
                marginTop: 34,
              }}
            >
              <button
                type="button"
                onClick={() => (signedIn ? undefined : openAuth("register"))}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: 52,
                  padding: "0 24px",
                  border: 0,
                  borderRadius: 16,
                  background: "#241607",
                  color: "#fff7df",
                  fontWeight: 800,
                  fontFamily: "inherit",
                  fontSize: 15,
                  cursor: "pointer",
                  boxShadow: "0 20px 42px rgba(36, 22, 7, 0.24)",
                }}
              >
                {signedIn ? "Dán link bên dưới để bắt đầu" : "Dùng thử bot"}
              </button>
              <a
                href="#how-it-works"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: 52,
                  padding: "0 22px",
                  borderRadius: 16,
                  color: "#2d1a04",
                  textDecoration: "none",
                  fontWeight: 800,
                  background: "rgba(255,255,255,0.55)",
                  border: "1px solid rgba(80, 48, 0, 0.14)",
                }}
              >
                Xem cách hoạt động
              </a>
            </div>

            <form onSubmit={convertLink} style={{ marginTop: 24, maxWidth: 620 }}>
              <label
                style={{
                  display: "grid",
                  gap: 8,
                  color: "#62451c",
                  fontWeight: 800,
                }}
              >
                Dán link Shopee để chuyển đổi
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <input
                    value={sourceUrl}
                    onChange={(event) => setSourceUrl(event.target.value)}
                    placeholder="https://shopee.vn/..."
                    required
                    style={{
                      flex: "1 1 280px",
                      minHeight: 50,
                      padding: "0 15px",
                      border: "1px solid rgba(80, 48, 0, 0.2)",
                      borderRadius: 12,
                      background: "rgba(255,255,255,.72)",
                      fontSize: 15,
                      fontFamily: "inherit",
                    }}
                  />
                  <button
                    type="submit"
                    disabled={converting}
                    style={{
                      minHeight: 50,
                      padding: "0 18px",
                      border: 0,
                      borderRadius: 12,
                      background: "#ffc928",
                      color: "#241607",
                      fontWeight: 800,
                      fontFamily: "inherit",
                      cursor: "pointer",
                    }}
                  >
                    {converting ? "Đang tạo..." : "Chuyển đổi"}
                  </button>
                </div>
              </label>
              {convertedLink && (
                <div
                  style={{
                    marginTop: 12,
                    padding: 14,
                    borderRadius: 12,
                    background: "rgba(255,255,255,.62)",
                    color: "#583600",
                    wordBreak: "break-all",
                  }}
                >
                  <strong>{convertedLink.tracking_id}</strong>
                  <br />
                  {convertedLink.affiliate_url}
                </div>
              )}
              {error && (
                <p style={{ margin: "10px 0 0", color: "#b42318" }}>{error}</p>
              )}
            </form>
          </div>

          <aside
            aria-label="Bảng minh họa hoàn tiền"
            style={{
              position: "relative",
              padding: 22,
              borderRadius: 34,
              background: "rgba(255,255,255,0.58)",
              border: "1px solid rgba(92, 60, 7, 0.14)",
              boxShadow: "0 32px 90px rgba(114, 72, 8, 0.18)",
              backdropFilter: "blur(18px)",
            }}
          >
            <div
              style={{
                borderRadius: 26,
                padding: 24,
                background: "#241607",
                color: "#fff7df",
                minHeight: 420,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 28,
                }}
              >
                <span style={{ fontWeight: 800 }}>Bee Wallet</span>
                <span
                  style={{
                    padding: "7px 10px",
                    borderRadius: 10,
                    background: "rgba(255, 201, 40, 0.16)",
                    color: "#ffc928",
                    fontSize: 12,
                    fontWeight: 800,
                  }}
                >
                  LIVE
                </span>
              </div>

              <p style={{ margin: 0, color: "#d5c2a1", fontSize: 14 }}>
                Hoàn tiền dự kiến
              </p>
              <div
                style={{
                  marginTop: 8,
                  fontSize: 58,
                  lineHeight: 1,
                  letterSpacing: "-0.06em",
                  fontWeight: 900,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                148.600đ
              </div>

              <div
                style={{
                  display: "grid",
                  gap: 12,
                  marginTop: 30,
                }}
              >
                {[
                  ["Máy xay mini", "+12.400đ"],
                  ["Tai nghe bluetooth", "+31.800đ"],
                  ["Áo chống nắng", "+18.900đ"],
                ].map(([name, value]) => (
                  <div
                    key={name}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 16,
                      padding: "14px 0",
                      borderBottom: "1px solid rgba(255,255,255,0.1)",
                    }}
                  >
                    <span style={{ color: "#ead9b9" }}>{name}</span>
                    <strong style={{ color: "#ffc928" }}>{value}</strong>
                  </div>
                ))}
              </div>

              <div
                style={{
                  marginTop: 30,
                  padding: 18,
                  borderRadius: 20,
                  background:
                    "linear-gradient(135deg, rgba(255, 201, 40, 0.96), rgba(255, 160, 48, 0.92))",
                  color: "#241607",
                }}
              >
                <strong style={{ display: "block", marginBottom: 6 }}>
                  Link vừa tạo
                </strong>
                <span style={{ color: "#583600", wordBreak: "break-all" }}>
                  beehoantien.vn/s/8kQp2x
                </span>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section
        id="how-it-works"
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "0 24px 92px",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "0.85fr 1.15fr",
            gap: 30,
            alignItems: "start",
          }}
        >
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: "clamp(34px, 5vw, 62px)",
                lineHeight: 0.96,
                letterSpacing: "-0.06em",
                textWrap: "balance",
              }}
            >
              Một bot nhỏ cho cả luồng affiliate.
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 10,
                marginTop: 28,
              }}
            >
              {stats.map(([value, label]) => (
                <div
                  key={label}
                  style={{
                    padding: 16,
                    borderRadius: 18,
                    background: "rgba(255,255,255,0.5)",
                  }}
                >
                  <strong
                    style={{
                      display: "block",
                      fontSize: 24,
                      letterSpacing: "-0.04em",
                    }}
                  >
                    {value}
                  </strong>
                  <span style={{ color: "#715326", fontSize: 13 }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: "grid", gap: 14 }}>
            {steps.map((step) => (
              <article
                key={step.label}
                style={{
                  display: "grid",
                  gridTemplateColumns: "70px 1fr",
                  gap: 18,
                  padding: 22,
                  borderRadius: 26,
                  background: "rgba(255,255,255,0.54)",
                  border: "1px solid rgba(91, 59, 8, 0.12)",
                }}
              >
                <span
                  style={{
                    color: "#9b6a00",
                    fontWeight: 900,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {step.label}
                </span>
                <div>
                  <h3
                    style={{
                      margin: "0 0 8px",
                      fontSize: 23,
                      letterSpacing: "-0.035em",
                    }}
                  >
                    {step.title}
                  </h3>
                  <p
                    style={{
                      margin: 0,
                      color: "#684b20",
                      lineHeight: 1.65,
                    }}
                  >
                    {step.text}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <footer
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "26px 24px 38px",
          display: "flex",
          justifyContent: "space-between",
          gap: 18,
          flexWrap: "wrap",
          color: "#745729",
          borderTop: "1px solid rgba(80, 48, 0, 0.12)",
        }}
      >
        <span>© 2026 Bee Hoàn Tiền</span>
        <span>Liên hệ: 0967913855 · hqvinh2210@gmail.com</span>
      </footer>
    </main>
  );
}
