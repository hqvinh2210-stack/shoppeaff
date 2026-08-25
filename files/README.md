# giatotday-shortener

Dịch vụ rút gọn link affiliate Shopee, dạng `https://giatotday.vn/affiliate/<code>`.

## Kiến trúc
- **Next.js** (App Router, Route Handlers) — deploy free trên Vercel, gắn domain riêng dễ dàng.
- **Supabase** (Postgres) — bảng `short_links` lưu mapping mã ngắn ↔ link gốc, `short_link_clicks` log lượt click.
- Mã ngắn 8 ký tự (nanoid, bỏ ký tự dễ nhầm `0/O/1/l/I`) — vd `VIQiou9E`.
- Chỉ cho phép rút gọn link trỏ tới domain Shopee/an_redir (chặn bị lợi dụng làm open-redirect).

## Cài đặt

```bash
npm install
```

Tạo `.env.local` từ `.env.example`, điền:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — lấy trong Supabase Project Settings → API (dùng **service role key**, không phải anon key).
- `SHORTENER_API_KEY` — tự đặt 1 chuỗi bí mật bất kỳ, dùng để bot gọi API tạo link (tránh ai cũng tạo được link rác).
- `SHORTENER_PUBLIC_BASE_URL` — domain public, vd `https://giatotday.vn`.

Chạy migration `supabase/migrations/001_short_links.sql` trong Supabase SQL Editor để tạo bảng.

## Chạy local

```bash
npm run dev
```

## Deploy lên Vercel
1. Đẩy code lên GitHub, import repo vào Vercel.
2. Khai báo các biến env ở trên trong Vercel Project Settings.
3. Gắn domain `giatotday.vn` vào project (Vercel → Domains), trỏ DNS theo hướng dẫn Vercel đưa ra.

## API

**POST `/api/shorten`** — tạo link rút gọn (gọi từ bot Telegram/Zalo)
```
Header: X-API-Key: <SHORTENER_API_KEY>
Body: { "targetUrl": "https://s.shopee.vn/an_redir?...", "itemId": "1589295236", "source": "telegram" }
→ { "status": "success", "code": "VIQiou9E", "shortUrl": "https://giatotday.vn/affiliate/VIQiou9E" }
```

**GET `/affiliate/:code`** — redirect 302 tới link gốc, tự log click.
