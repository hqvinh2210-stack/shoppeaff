# Đặc tả Role nghiệp vụ – Tính năng – Ràng buộc Frontend/Backend

Hệ thống: **Bee Hoàn Tiền** (Cashback Affiliate System)
Phạm vi: Next.js 16 frontend (`app/`), FastAPI backend (`backend/`), bot Zalo (`index.mjs`), bot Telegram (`bot.py`), short-link Supabase (`lib/`).
Tài liệu này được viết lại từ mã nguồn thực tế (không phải từ mong muốn thiết kế). Mục 6 liệt kê các điểm mã nguồn hiện **chưa khớp** với đặc tả này.

---

## 1. Bản đồ hệ thống

```
                    ┌──────────────────────────┐
  Người dùng ──────▶│ Next.js FE (:3000)       │──── Bearer JWT ───┐
                    │ /, /login, /register,    │                   │
                    │ /dashboard, /withdrawals,│                   ▼
                    │ /admin                   │      ┌────────────────────────┐
                    └──────────────────────────┘      │ FastAPI (:8000)        │
                    ┌──────────────────────────┐      │ /api/v1/**             │
  Người dùng ──────▶│ Bot Telegram (bot.py)    │─────▶│ auth, users, wallet,   │
                    │ Bot Zalo (index.mjs)     │      │ orders, affiliate,     │
                    └──────────────────────────┘      │ withdrawals, admin,    │
                    ┌──────────────────────────┐      │ zalo, telegram,        │
  AccessTrade ─────▶│ Webhook / Sync worker    │─────▶│ webhooks               │
                    └──────────────────────────┘      └───────────┬────────────┘
                    ┌──────────────────────────┐                  │
  Người click ─────▶│ Next.js /[code] redirect │──▶ Supabase       ▼
                    └──────────────────────────┘   short_links   PostgreSQL
```

Có **hai kho dữ liệu song song** — đây là ràng buộc kiến trúc quan trọng nhất:

| Kho | Chủ sở hữu | Bảng chính | Dùng cho |
|---|---|---|---|
| PostgreSQL (SQLAlchemy) | Backend FastAPI | `users`, `wallets`, `orders`, `affiliate_links`, `affiliate_clicks`, `affiliate_orders`, `cashback_transactions`, `withdrawals` | Toàn bộ nghiệp vụ tiền |
| Supabase | Next.js route handler | `short_links`, `short_link_clicks` | Chỉ rút gọn link + đếm click |

**Ràng buộc:** Supabase KHÔNG được chứa dữ liệu tiền. Mọi số dư, đơn hàng, giao dịch chỉ tồn tại ở PostgreSQL và chỉ truy cập qua FastAPI.

---

## 2. Role nghiệp vụ

### 2.1 Danh sách role

| Mã role | Tên | Nguồn định danh | Lưu ở đâu |
|---|---|---|---|
| `GUEST` | Khách vãng lai | Không có token | — |
| `USER` | Người dùng hoàn tiền | JWT access token, `sub = users.id` | `users.role = 'USER'` (mặc định) |
| `ADMIN` | Quản trị vận hành | JWT access token + `users.role = 'ADMIN'` | `users.role` |
| `BOT_TELEGRAM` | Bot Telegram | `telegram_user_id` đã liên kết | `telegram_accounts` |
| `BOT_ZALO` | Bot Zalo | `zalo_user_id` đã liên kết | `zalo_accounts` |
| `NETWORK` | Mạng affiliate (AccessTrade/Shopee) | Chữ ký webhook + `Idempotency-Key` | — |
| `SYSTEM` | Worker nền (sync, duyệt cashback) | Chạy trong tiến trình backend | — |

### 2.2 Định nghĩa từng role

#### GUEST — Khách
- **Được làm:** xem landing page, đăng ký, đăng nhập (mật khẩu hoặc Google), truy cập link rút gọn `/{code}`.
- **Không được làm:** tạo link affiliate, xem ví, xem đơn, rút tiền.
- **Ràng buộc FE:** nút "Chuyển đổi link" ở trang chủ phải mở form đăng nhập thay vì gọi API khi chưa có token.
- **Ràng buộc BE:** mọi endpoint trừ `/auth/register`, `/auth/login`, `/auth/google`, `/health`, `/webhooks/*` đều trả `401` khi thiếu Bearer token.

#### USER — Người dùng hoàn tiền
Là chủ thể trung tâm. Mỗi user có đúng **một ví** (`wallets.user_id` unique), **một dải tracking riêng**, tối đa **một tài khoản Zalo active** và **một tài khoản Telegram active**.

- **Được làm:**
  1. Quản lý tài khoản: đăng ký / đăng nhập / đăng xuất, xem hồ sơ.
  2. Tạo link affiliate từ URL Shopee (qua web, Telegram hoặc Zalo).
  3. Xem danh sách link đã tạo của **chính mình**.
  4. Xem ví: `available_balance` (khả dụng) và `pending_balance` (chờ duyệt).
  5. Xem đơn hàng và trạng thái hoàn tiền của **chính mình**.
  6. Xem lịch sử giao dịch ví của **chính mình**.
  7. Liên kết / hủy liên kết Zalo, liên kết Telegram.
  8. Tạo yêu cầu rút tiền và xem lịch sử rút.
- **Không được làm:** xem dữ liệu user khác, tự đổi số dư, tự đổi trạng thái đơn, duyệt rút tiền, đổi tỉ lệ hoàn tiền.
- **Ràng buộc dữ liệu:** mọi truy vấn ở BE **bắt buộc** kèm `WHERE user_id = current_user.id`. Không endpoint nào cho phép client truyền `user_id`.

#### ADMIN — Quản trị vận hành
- **Được làm:** xem danh sách user, xem toàn bộ đơn, xem báo cáo hoàn tiền theo tháng, xem đơn cần đối soát thủ công (`ATTRIBUTION_REVIEW`), xem toàn bộ yêu cầu rút, **duyệt / từ chối** yêu cầu rút, đề xuất tỉ lệ hoàn tiền.
- **Không được làm:** sửa trực tiếp số dư ví, xóa `cashback_transactions`, sửa `withdrawals.amount` sau khi tạo.
- **Ràng buộc BE:** toàn bộ `/api/v1/admin/**` đi qua `require_admin` → `403` nếu `users.role != 'ADMIN'`.
- **Ràng buộc FE:** tab "Báo cáo" chỉ hiện khi hồ sơ trả về `role = 'ADMIN'`; tài khoản thường mở URL `/admin` sẽ nhận thông báo thiếu quyền chứ không thấy số liệu. **FE phải coi 403 là lớp phòng thủ cuối, không phải cơ chế phân quyền chính.**

#### BOT_TELEGRAM / BOT_ZALO — Kênh chat
Bot **không phải** một danh tính độc lập; bot chỉ là proxy hành động thay cho một USER đã liên kết.

- **Luồng liên kết bắt buộc:** USER đăng nhập web → BE cấp token liên kết TTL 15 phút → user gửi token cho bot → bot gọi endpoint xác nhận → BE tạo bản ghi `telegram_accounts` / `zalo_accounts`.
- **Ràng buộc:** một `telegram_user_id` / `zalo_user_id` chỉ gắn với **một** `users.id`; một user chỉ có **một** tài khoản kênh `ACTIVE`; token liên kết **dùng một lần** (`used_at`), hết hạn thì `status = EXPIRED`.
- **Khi chưa liên kết:** bot chỉ được trả thông tin sản phẩm công khai, **không** được tạo link tracking gắn cho bất kỳ user nào; BE trả `401` / `ACCOUNT_NOT_LINKED`.

#### NETWORK — Mạng affiliate
- **Được làm:** đẩy dữ liệu đơn/hoa hồng vào BE qua webhook, hoặc để worker kéo về theo lịch.
- **Ràng buộc bắt buộc:**
  - Có **chữ ký hợp lệ** (HMAC) — không chỉ kiểm tra header tồn tại.
  - Có **`Idempotency-Key`**; gọi lại cùng key phải trả kết quả cũ, không tạo giao dịch mới.
  - Không được tự quyết `user_id`. Quy gán chủ đơn chỉ dựa trên `tracking_id` do hệ thống sinh.

#### SYSTEM — Worker nền
- `accesstrade_sync`: kéo đơn + giao dịch theo khoảng thời gian, upsert, đối soát cashback.
- `affiliate_sync`: upsert đơn từ provider theo `(platform, platform_order_id)`.
- `cashback_processor`: chuyển cashback từ `pending_balance` sang `available_balance` cho đơn `COMPLETED + SETTLED`.
- **Ràng buộc:** worker **không được** cộng/trừ số dư trực tiếp; mọi thay đổi số dư phải qua `WalletService` để sinh bản ghi `cashback_transactions` bất biến.

### 2.3 Ma trận quyền (tóm tắt)

| Chức năng | GUEST | USER | ADMIN | BOT | NETWORK |
|---|:---:|:---:|:---:|:---:|:---:|
| Đăng ký / đăng nhập | ✅ | — | — | — | — |
| Xem hồ sơ của mình | ❌ | ✅ | ✅ | — | — |
| Tạo link affiliate | ❌ | ✅ | ✅ | ✅ (thay user) | — |
| Xem link của mình | ❌ | ✅ | ✅ | — | — |
| Xem ví / giao dịch | ❌ | ✅ | ✅ | — | — |
| Xem đơn của mình | ❌ | ✅ | ✅ | — | — |
| Liên kết Zalo/Telegram | ❌ | ✅ | ✅ | ✅ (xác nhận) | — |
| Tạo yêu cầu rút | ❌ | ✅ | ✅ | — | — |
| Duyệt / từ chối rút | ❌ | ❌ | ✅ | — | — |
| Xem mọi user / mọi đơn | ❌ | ❌ | ✅ | — | — |
| Báo cáo hoàn tiền tháng | ❌ | ❌ | ✅ | — | — |
| Đẩy đơn / hoa hồng | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 3. Danh mục tính năng

### F1. Xác thực & tài khoản

| ID | Tính năng | Role | FE | BE |
|---|---|---|---|---|
| F1.1 | Đăng ký email/SĐT + mật khẩu | GUEST | lớp phủ (mọi trang) | `POST /auth/register` |
| F1.2 | Đăng nhập | GUEST | lớp phủ (mọi trang) | `POST /auth/login` |
| F1.3 | Đăng nhập Google (One Tap) | GUEST | lớp phủ (mọi trang) | `POST /auth/google` |
| F1.4 | Xem hồ sơ | USER | `/dashboard` | `GET /auth/me`, `GET /users/me` |
| F1.5 | Đăng xuất | USER | mọi trang | `POST /auth/logout` (FE tự xóa token) |
| F1.6 | Làm mới phiên | USER | ngầm | `POST /auth/refresh` |
| F1.7 | Thư chào mừng khi tạo tài khoản | SYSTEM | — | `EmailService.send_welcome` (chạy nền) |

**Quy tắc nghiệp vụ**
- Đăng ký phải có ít nhất một trong `email` hoặc `phone`, nếu không → `400`.
- `email` và `phone` duy nhất toàn hệ thống → trùng trả `409`.
- Mật khẩu tối thiểu 8 ký tự (validate ở cả FE `minLength=8` và BE `Field(min_length=8)`).
- Đăng ký thành công tự sinh `user_code = USR_{id}` và tạo ví số dư 0.
- Google: chỉ chấp nhận khi `aud` khớp `GOOGLE_CLIENT_ID` và `email_verified = true`; email chưa tồn tại thì tạo user mới (không có mật khẩu).
- User `status != ACTIVE` → `403` ở mọi endpoint cần đăng nhập.
- Đăng ký thành công **có email** → gửi thư chào mừng qua SMTP, chạy trong
  `BackgroundTasks` nên không làm chậm phản hồi. Đăng ký bằng số điện thoại thì bỏ qua.
- Đăng nhập Google chỉ gửi thư khi **tài khoản vừa được tạo mới**, không gửi lại mỗi lần đăng nhập.
- **Email không bao giờ được làm hỏng nghiệp vụ:** SMTP hỏng, sai mật khẩu hay chưa cấu hình
  đều chỉ ghi log và trả `False`; người dùng vẫn đăng ký thành công.

### F2. Tạo & quản lý link affiliate

| ID | Tính năng | Role | FE | BE |
|---|---|---|---|---|
| F2.1 | Tạo link tracking (mock/Shopee) | USER | `/`, `/dashboard` | `POST /affiliate/generate-link` |
| F2.2 | Tạo link qua AccessTrade | USER | *(chưa có UI)* | `POST /affiliate/accesstrade/link` |
| F2.3 | Danh sách link của tôi | USER | `/dashboard` | `GET /affiliate/links` |
| F2.4 | Tạo link từ Telegram | BOT | bot | `POST /telegram/generate-link` |
| F2.5 | Tạo link từ Zalo | BOT | bot | `POST /webhooks/zalo` |
| F2.6 | Rút gọn link + đếm click | GUEST | `/{code}` | Supabase `short_links` |

**Quy tắc nghiệp vụ**
- URL đầu vào chỉ chấp nhận host `shopee.vn` (và subdomain). URL khác → `400` kèm thông điệp tiếng Việt.
- Chuẩn hóa URL: ép `https`, hạ thường host, bỏ dấu `/` cuối, **chỉ giữ query `sp_atk`**, bỏ fragment. Mục đích: cùng một sản phẩm không sinh nhiều bản ghi rác.
- Tách `shop_id` / `product_id` theo pattern `i.{shop}.{product}` hoặc `product/{shop}/{product}`; không tách được vẫn cho tạo link, hai trường để `null`.
- **Hai hệ tracking song song, không được trộn:**
  - Kênh mock/Shopee: `tracking_id = CB_{user_id}_{affiliate_link_id}` (bảng `affiliate_links`).
  - Kênh AccessTrade: `tracking_id = trk_{uuid4hex}`, gán vào `sub1` (bảng `affiliate_clicks`).
- `tracking_id` **unique toàn hệ thống** ở cả hai bảng.
- Rút gọn link chỉ được trỏ tới `s.shopee.vn`, `shopee.vn`, `vn.shp.ee` — chặn open-redirect.

### F3. Ghi nhận đơn & quy gán

| ID | Tính năng | Role | BE |
|---|---|---|---|
| F3.1 | Nhận webhook đơn hàng | NETWORK | `POST /affiliate/webhook` |
| F3.2 | Đồng bộ đơn AccessTrade | SYSTEM | `workers/accesstrade_sync.py` |
| F3.3 | Đồng bộ đơn provider | SYSTEM | `workers/affiliate_sync.py` |
| F3.4 | Xem đơn của tôi | USER | `GET /orders`, `GET /orders/{id}` |
| F3.5 | Xem đơn cần đối soát | ADMIN | `GET /admin/orders/attribution-review` |

**Quy tắc nghiệp vụ**
- Khóa chống trùng: `UNIQUE(platform, platform_order_id)` cho `orders`; `UNIQUE(network, merchant, external_order_id)` cho `affiliate_orders`.
- Quy gán chủ đơn:
  - Có `tracking_id` khớp `affiliate_links` → gán `user_id`, `affiliate_link_id`, giữ nguyên `order_status` từ mạng.
  - Không có / không khớp → `order_status = ATTRIBUTION_REVIEW`, `cashback_status = REVIEW`, `cashback_amount = 0`, chờ ADMIN xử lý.
  - Đơn AccessTrade không khớp click → ghi vào `unmatched_affiliate_orders`, chỉ ghi **một lần** cho mỗi đơn chưa resolved.
- Đơn đã có chủ thì **không đổi chủ** khi webhook gọi lại (`existing.user_id or user_id`).
- Cashback = `commission_amount × CASHBACK_RATE_PERCENT / 100`, làm tròn 2 chữ số. Mặc định `70%`.
- Điều kiện đủ để ghi cashback `PENDING`:
  `order_status ∈ {PENDING, CONFIRMED, COMPLETED}` **và** `commission_status ∈ {PENDING, CONFIRMED, SETTLED}`.

### F4. Ví & sổ cái

| ID | Tính năng | Role | FE | BE |
|---|---|---|---|---|
| F4.1 | Xem số dư | USER | `/dashboard` | `GET /wallet` |
| F4.2 | Lịch sử giao dịch | USER | `/dashboard` | `GET /wallet/transactions` |
| F4.3 | Duyệt cashback | SYSTEM | — | `workers/cashback_processor.py` |
| F4.4 | Đối soát / thu hồi cashback | SYSTEM | — | `CashbackReconciliationService` |

**Quy tắc bất biến (non-negotiable)**
1. Số dư ví **chỉ** được thay đổi bên trong `WalletService`. Không service/worker/endpoint nào được `UPDATE wallets` trực tiếp.
2. Mỗi lần đổi số dư phải sinh **một** `cashback_transactions` ghi rõ `balance_before`, `balance_after`, `reference_code` (unique). Bản ghi này **bất biến** — không sửa, không xóa.
3. Cộng cashback `PENDING` **idempotent** theo `(order_id, transaction_type = CASHBACK_PENDING)`.
4. Duyệt cashback **idempotent** theo `(order_id, affiliate_transaction_id, CASHBACK_APPROVED)`.
5. Không được duyệt vượt `pending_balance` → `ValueError`.
6. Không được thu hồi (`REVERSED`) vượt `available_balance` → `ValueError`.
7. Vòng đời tiền: `PENDING → APPROVED → (rút hoặc REVERSED)`.

**Máy trạng thái `cashback_status`**

```
NONE ──(đủ điều kiện)──▶ PENDING ──(đơn COMPLETED + SETTLED)──▶ APPROVED
 ▲                          │                                      │
 └──(mất điều kiện)─────────┘                       (mạng hủy) ────▶ REVERSED

REVIEW ──(admin quy gán thủ công)──▶ PENDING
```

### F5. Rút tiền

| ID | Tính năng | Role | FE | BE |
|---|---|---|---|---|
| F5.1 | Tạo yêu cầu rút | USER | `/withdrawals` | `POST /withdrawals` |
| F5.2 | Lịch sử rút của tôi | USER | `/withdrawals` | `GET /withdrawals` |
| F5.3 | Danh sách rút toàn hệ thống | ADMIN | `/admin` | `GET /admin/withdrawals` |
| F5.4 | Duyệt rút | ADMIN | `/admin` | `POST /admin/withdrawals/{id}/approve` |
| F5.5 | Từ chối rút | ADMIN | `/admin` | `POST /admin/withdrawals/{id}/reject` |

**Quy tắc nghiệp vụ**
- `amount > 0` và `amount >= MINIMUM_WITHDRAWAL_AMOUNT` (**mặc định 30.000đ**) → không đạt trả `400` kèm thông điệp tiếng Việt.
- `method` phải thuộc enum `WithdrawalMethod` (`BANK`, `MOMO`) → sai trả `422`.
- `method = BANK` **bắt buộc** có `bank_code`; ví điện tử để trống → thiếu trả `422`.
- `account_name` lưu dạng **IN HOA không dấu**; FE chuẩn hoá ngay khi gõ, BE chỉ kiểm độ dài.
- `amount <= available_balance` → vượt trả `400`.
- Tạo yêu cầu **giữ tiền ngay**: trừ `available_balance` và ghi giao dịch `WITHDRAWAL` (số âm, trạng thái `PENDING`).
- Từ chối → hoàn `available_balance` bằng giao dịch `WITHDRAWAL_REJECTED`, ghi `rejection_reason`.
- Duyệt → `status = COMPLETED`, **không** ghi thêm giao dịch (tiền đã trừ lúc tạo).
- Yêu cầu đã `COMPLETED` hoặc `REJECTED` là **trạng thái cuối**, không đổi tiếp được.
- Máy trạng thái: `PENDING → PROCESSING → COMPLETED` | `PENDING → REJECTED`.

### F6. Liên kết kênh chat

| ID | Tính năng | Role | FE | BE |
|---|---|---|---|---|
| F6.1 | Tạo token liên kết Zalo | USER | *(chưa có UI)* | `POST /zalo/link` |
| F6.2 | Trạng thái liên kết Zalo | USER | *(chưa có UI)* | `GET /zalo/status` |
| F6.3 | Hủy liên kết Zalo | USER | *(chưa có UI)* | `DELETE /zalo/unlink` |
| F6.4 | Tạo token liên kết Telegram | USER | `/dashboard` | `POST /telegram/link` |
| F6.5 | Xác nhận liên kết Telegram | BOT | lệnh `/link <token>` | `POST /telegram/link/confirm` |

**Quy tắc nghiệp vụ**
- Token liên kết: `token_urlsafe(32)`, TTL **15 phút**, dùng **một lần**.
- Token đã dùng hoặc hết hạn → `400`, đồng thời đánh dấu `status = EXPIRED`.
- `zalo_user_id` đã gắn user khác → `400` ("already linked to another user").
- User đã có tài khoản kênh `ACTIVE` khác → `400`.
- Hủy liên kết = chuyển `status = INACTIVE` (không xóa bản ghi, giữ vết audit).

### F7. Quản trị & báo cáo

| ID | Tính năng | Role | BE |
|---|---|---|---|
| F7.1 | Danh sách user (200 gần nhất) | ADMIN | `GET /admin/users` |
| F7.2 | Danh sách đơn (500 gần nhất) | ADMIN | `GET /admin/orders` |
| F7.3 | Báo cáo hoàn tiền theo tháng | ADMIN | `GET /admin/cashback/monthly?year&month` |
| F7.4 | Đơn chờ đối soát | ADMIN | `GET /admin/orders/attribution-review` |
| F7.5 | Đặt tỉ lệ hoàn tiền | ADMIN | `POST /admin/cashback-rates` *(mới chỉ nhận, chưa lưu)* |

**Quy tắc:** báo cáo tháng tính `net_cashback = Σ(CASHBACK_APPROVED) + Σ(CASHBACK_REVERSED)` (bản ghi `REVERSED` mang số âm nên phép cộng là đúng), lọc `created_at` trong `[đầu tháng, đầu tháng sau)` theo UTC.

---

## 4. Hợp đồng API — ràng buộc Frontend ↔ Backend

### 4.1 Ràng buộc nền tảng

| Hạng mục | Quy định |
|---|---|
| Base URL | FE đọc `NEXT_PUBLIC_API_URL`, mặc định `http://localhost:8000/api/v1`. **Không hardcode URL trong component.** |
| Định dạng | Request/response `application/json`, UTF-8. |
| Xác thực | Header `Authorization: Bearer <access_token>`. Không dùng cookie, không dùng session. |
| Lưu token | FE lưu khóa `cashback_access_token` trong `localStorage`. Mọi trang phải dùng đúng khóa này. |
| Lỗi | BE luôn trả `{"detail": "<thông điệp>"}`. FE **bắt buộc** đọc `data.detail` để hiển thị, không tự chế thông điệp khi BE đã trả. |
| Số tiền | BE serialize `Decimal` thành **chuỗi**. FE phải `Number(value)` trước khi tính/format, hiển thị theo `vi-VN` + hậu tố `đ`. |
| Thời gian | ISO-8601 có timezone (UTC). FE tự đổi sang giờ Việt Nam khi hiển thị. |
| CORS | BE khai báo origin của FE theo môi trường qua biến môi trường, không hardcode `localhost:3000`. |
| Tên trường | `snake_case` xuyên suốt. FE **không** đổi tên trường khi map sang type TS. |

### 4.2 Quy ước mã lỗi

| HTTP | Ý nghĩa | FE phải làm gì |
|---|---|---|
| `200/201` | Thành công | Cập nhật state |
| `204` | Thành công, không nội dung | **Không** parse JSON |
| `400` | Dữ liệu/nghiệp vụ không hợp lệ | Hiện `detail` cạnh form, giữ nguyên dữ liệu đã nhập |
| `401` | Thiếu/sai/hết hạn token | Xóa `cashback_access_token`, chuyển về `/` hoặc `/login` |
| `403` | Không đủ quyền hoặc user bị khóa | Hiện "Bạn không có quyền", **không** xóa token |
| `404` | Không tìm thấy | Hiện trạng thái rỗng |
| `409` | Trùng dữ liệu (email/SĐT) | Hiện lỗi tại đúng ô nhập |
| `422` | Sai schema (Pydantic) | Là **lỗi lập trình FE** — phải sửa payload, không hiện raw cho user |
| `503` | Tích hợp ngoài chưa cấu hình | Ẩn/khóa tính năng, hiện "Tính năng tạm chưa khả dụng" |

### 4.3 Bảng hợp đồng chi tiết

| Endpoint | Method | Auth | Request | Response | Ràng buộc FE |
|---|---|---|---|---|---|
| `/auth/register` | POST | — | `{email?, phone?, password, full_name?}` | `201 {access_token, refresh_token, token_type}` | Phải gửi ít nhất `email` hoặc `phone`; `password >= 8` |
| `/auth/login` | POST | — | `{identifier, password}` | `200 TokenPair` | `identifier` là email **hoặc** SĐT — một trường duy nhất |
| `/auth/google` | POST | — | `{id_token}` | `200 TokenPair` | Chỉ render nút Google khi có `NEXT_PUBLIC_GOOGLE_CLIENT_ID` |
| `/auth/me` | GET | USER | — | `UserRead` | Dùng để khôi phục phiên khi load trang |
| `/auth/refresh` | POST | — | `{refresh_token}` | `200 TokenPair` | Tự gọi khi gặp `401`, một lần cho mỗi request |
| `/auth/logout` | POST | — | — | `{status}` | FE **phải tự** xoá cả access lẫn refresh token; BE không thu hồi |
| `/admin/summary` | GET | ADMIN | — | `{users, pending_withdrawals, attribution_review_orders, total_available_balance, total_pending_balance}` | Dải số liệu đầu trang `/admin` |
| `/wallet` | GET | USER | — | `{available_balance, pending_balance, currency, updated_at}` | Tự tạo ví nếu chưa có |
| `/wallet/transactions` | GET | USER | — | `TransactionRead[]` | Sắp xếp mới nhất trước |
| `/orders` | GET | USER | — | `OrderRead[]` | **Không** phân trang → FE tự giới hạn hiển thị |
| `/orders/{id}` | GET | USER | — | `OrderRead` | `404` nếu đơn không thuộc user |
| `/affiliate/generate-link` | POST | USER | `{original_url}` | `201 AffiliateLinkRead` | URL không phải Shopee → `400` |
| `/affiliate/accesstrade/link` | POST | USER | `{original_url}` | `201 {tracking_id, affiliate_url, short_url, url_origin}` | Schema **khác** `AffiliateLinkRead`, không dùng chung type |
| `/affiliate/links` | GET | USER | — | `AffiliateLinkRead[]` | Chỉ link của user hiện tại |
| `/withdrawals` | POST | USER | `{amount, method, bank_code?, bank_name?, account_name, account_number}` | `201 WithdrawalRead` | `method` từ enum; `BANK` bắt buộc kèm `bank_code` |
| `/withdrawals` | GET | USER | — | `WithdrawalRead[]` | — |
| `/zalo/link` | POST | USER | — | `{token, expires_at, link_url}` | Hiển thị đếm ngược 15 phút |
| `/zalo/status` | GET | USER | — | `{linked, zalo_user_id?, status?}` | — |
| `/zalo/unlink` | DELETE | USER | — | `204` | Không gọi `response.json()` |
| `/telegram/link` | POST | USER | — | `{token, expires_at, command}` | Hiện `command` để user copy |
| `/admin/cashback/monthly` | GET | ADMIN | query `year`, `month` | `{year, month, total_cashback, users[]}` | `year ∈ [2020,2100]`, `month ∈ [1,12]` — FE chặn trước |
| `/admin/withdrawals/{id}/approve` | POST | ADMIN | — | `{status, withdrawal_id}` | — |
| `/admin/withdrawals/{id}/reject` | POST | ADMIN | **query** `reason` | `{status, withdrawal_id}` | `reason` là **query param**, không phải body |
| `/affiliate/webhook` | POST | NETWORK | header `Idempotency-Key` + `{orders[]}` | `OrderRead[]` | FE **không bao giờ** gọi |
| `/webhooks/zalo` | POST | NETWORK | header `X-Zalo-Signature` + `{sender, message?, token?}` | `{status, ...}` | FE **không bao giờ** gọi |

### 4.4 Ràng buộc giá trị enum (FE phải khớp tuyệt đối)

FE **không được** tự định nghĩa tập giá trị trạng thái. Nguồn sự thật là `backend/app/models/enums.py`, được phản chiếu sang frontend tại **`lib/status.ts`** (`@/lib/status`). Component chỉ được import từ file này, không viết chuỗi trạng thái trực tiếp trong JSX.

| Enum | Giá trị hợp lệ |
|---|---|
| `UserStatus` | `ACTIVE`, `INACTIVE`, `BLOCKED` |
| `OrderStatus` | `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `REVERSED`, `ATTRIBUTION_REVIEW` |
| `CommissionStatus` | `PENDING`, `CONFIRMED`, `SETTLED`, `REJECTED`, `REVERSED` |
| `CashbackStatus` | `NONE`, `PENDING`, `APPROVED`, `REVERSED`, `REVIEW` |
| `TransactionType` | `CASHBACK_PENDING`, `CASHBACK_APPROVED`, `CASHBACK_REVERSED`, `WITHDRAWAL`, `WITHDRAWAL_REJECTED`, `ADJUSTMENT` |
| `TransactionStatus` | `PENDING`, `COMPLETED`, `REVERSED`, `REJECTED` |
| `WithdrawalStatus` | `PENDING`, `PROCESSING`, `COMPLETED`, `REJECTED` |
| `LinkStatus` | `ACTIVE`, `INACTIVE`, `EXPIRED`, `USED` |

**Nhãn tiếng Việt hiển thị** — BE luôn trả mã tiếng Anh, FE map qua các bảng `*_STATUS_META` trong `lib/status.ts`:

| Mã | Nhãn |
|---|---|
| `NONE` | Chưa ghi nhận |
| `PENDING` | Đang chờ / Chờ duyệt |
| `APPROVED` | Đã duyệt |
| `REVERSED` | Đã thu hồi |
| `REVIEW` | Chờ đối soát |
| `ATTRIBUTION_REVIEW` | Chờ quy gán |
| `COMPLETED` | Hoàn tất |
| `REJECTED` | Bị từ chối |
| `PROCESSING` | Đang chi trả |

Hàm `statusLabel()` trả lại **đúng mã gốc** khi gặp giá trị chưa có trong bảng, để lỗi lệch hợp đồng lộ ra ngay trên UI thay vì bị nuốt mất.

**Phương thức rút tiền** cũng lấy từ `WITHDRAWAL_METHODS` trong cùng file (`BANK`, `MOMO`) — FE không hardcode chuỗi phương thức.

### 4.5 Ràng buộc validate hai lớp

Mọi ràng buộc dưới đây phải kiểm ở **cả FE (trải nghiệm) và BE (an toàn)**. FE kiểm để không gọi API vô ích; BE kiểm vì FE có thể bị bỏ qua.

| Trường | Ràng buộc | FE | BE |
|---|---|---|---|
| `password` | ≥ 8 ký tự | `minLength=8` | `Field(min_length=8)` |
| `email` | Đúng định dạng, duy nhất | `type="email"` | unique + `409` |
| `phone` | Duy nhất | — | unique + `409` |
| `original_url` | Host Shopee hợp lệ | regex trước khi gọi | `normalize_shopee_url` → `400` |
| `amount` (rút) | `> 0`, `>= 30.000`, `<= available_balance` | khoá nút + nêu rõ lý do dưới nút | `Field(gt=0)` + `ValueError` → `400` |
| `method` (rút) | Thuộc `WithdrawalMethod` | nút chọn, không nhập tự do | enum Pydantic → `422` |
| `bank_code` | Bắt buộc khi `method = BANK` | ẩn ô khi chọn ví điện tử | `model_validator` → `422` |
| `account_number` | Bắt buộc, không rỗng | `required` | `str` bắt buộc |
| `year` / `month` (báo cáo) | `2020..2100`, `1..12` | dùng `<select>` | `Query(ge=, le=)` |
| Token liên kết | ≥ 10 ký tự | — | `Field(min_length=10)` |

### 4.6 Ràng buộc phiên & điều hướng ở FE

Toàn bộ điều hướng đi qua khung chung `app/components/app-shell.tsx`: **thanh tab cố định trên cùng** + **lớp phủ đăng nhập**. Không màn hình nào được tự dựng lại header hay form đăng nhập riêng.

1. Khách chưa đăng nhập vẫn thấy **đủ mọi tab**. Bấm vào tab cần quyền → mở lớp phủ đăng nhập **ngay trên trang đang xem**, không điều hướng. Trang chủ luôn nhìn thấy phía sau.
2. Mở thẳng URL cần quyền (`/dashboard`, `/withdrawals`, `/admin`) khi chưa đăng nhập → render `SignInPrompt`, **không** redirect. Người dùng bấm tab "Trang chủ" là quay lại được.
3. `/login` và `/register` **không phải trang riêng** — chúng render lại trang chủ và AppShell tự mở lớp phủ ở đúng tab tương ứng. Đóng lớp phủ thì URL trở về `/`.
4. Phiên được khôi phục một lần ở `AuthProvider`; token hỏng/hết hạn thì dọn im lặng, khách vẫn xem được trang chủ.
5. Mọi lời gọi API đi qua `useAuth().request` (bọc `lib/api.ts`). Gặp `401` → tự dọn phiên **và** mở lớp phủ đăng nhập tại chỗ.
6. `403` → **không** xóa token, hiện thông báo thiếu quyền (trang `/admin` hiển thị "Tài khoản này không có quyền xem báo cáo vận hành").
7. Tab "Báo cáo" tự ẩn khi `UserRead.role` khác `ADMIN`. Quyền ADMIN cấp bằng `backend/scripts/create_admin.py`, không sửa tay trong DB.
5. Access token sống **30 phút**. FE phải xử lý được việc phiên hết hạn giữa chừng (hiện chỉ có cách đăng nhập lại — xem 6.2/C1).
6. Sau đăng nhập/đăng ký thành công: điều hướng `/dashboard`.
7. Sau đăng xuất: xóa token, về `/`.

### 4.7 Ràng buộc nhất quán dữ liệu FE ↔ BE

| Mã | Ràng buộc |
|---|---|
| **R1** | Số dư hiển thị trên FE luôn lấy từ `GET /wallet`, **không** tự cộng từ danh sách đơn. |
| **R2** | Sau khi tạo yêu cầu rút thành công, FE **phải** gọi lại `GET /wallet` vì `available_balance` đã đổi. |
| **R3** | Sau khi tạo link thành công, FE được phép prepend vào danh sách local (BE trả về bản ghi đầy đủ). |
| **R4** | FE **không** được tính lại `cashback_amount`; giá trị do BE chốt theo tỉ lệ tại thời điểm ghi nhận. |
| **R5** | FE **không** được hiển thị đơn `ATTRIBUTION_REVIEW` như đơn đã ghi nhận cho user — chúng chưa có chủ. |
| **R6** | Đơn AccessTrade nằm ở bảng `affiliate_orders`, **không** xuất hiện trong `GET /orders`. Ví có tiền mà danh sách đơn trống là do khoảng trống này (xem 6.1/B4). |
| **R7** | `tracking_id` FE nhận chỉ để hiển thị/copy, **không** dùng làm khóa gọi API. |
| **R8** | Danh sách trả về đã sắp xếp mới nhất trước; FE không sắp lại để tránh lệch khi thêm phân trang. |

---

## 5. Ràng buộc phi chức năng

| Hạng mục | Quy định |
|---|---|
| Bí mật | `SUPABASE_SERVICE_ROLE_KEY`, `TELEGRAM_BOT_TOKEN`, `ACCESSTRADE_API_TOKEN`, `JWT_SECRET`, `AFFILIATE_WEBHOOK_SECRET`, `ZALO_WEBHOOK_SECRET`, `TELEGRAM_BOT_SECRET` **chỉ** ở phía server. Không đặt tiền tố `NEXT_PUBLIC_`. |
| Fail closed | Thiếu bí mật xác thực thì endpoint webhook/bot trả `503`, tuyệt đối không cho đi qua. |
| `lib/supabase.ts` | Chỉ import trong Route Handler / Server Component. |
| Idempotency | Webhook và mọi thao tác ghi tiền phải idempotent. |
| Audit | Thao tác ADMIN (duyệt/từ chối rút, đổi tỉ lệ) phải ghi `audit_logs`. |
| Nhật ký | Không log token, mật khẩu, `account_number` đầy đủ. |
| Rate limit | `POST /affiliate/generate-link`, `/auth/login`, `/withdrawals` cần giới hạn theo user/IP. |
| Ngôn ngữ | Toàn bộ text hướng người dùng bằng tiếng Việt có dấu; file nguồn lưu **UTF-8 không BOM**. |
| Email | Nội dung HTML dùng bảng + style nội tuyến (client email bỏ qua `<style>`, flexbox, biến CSS). Luôn kèm bản plain text. Link dựng từ `APP_BASE_URL`. |
| Log | Log của `app.*` được cấu hình trong `create_app()`; nếu không, cảnh báo từ service bị nuốt hoàn toàn. |
| Tiền tệ | `VND`, hiển thị không phần lẻ, lưu `Numeric(18,2)`. |

---

## 6. Kết quả kiểm tra — các điểm mã nguồn chưa khớp đặc tả

### 6.1 Chặn nghiệp vụ / an toàn

| # | Vấn đề | Vị trí | Ảnh hưởng |
|---|---|---|---|
| ~~B1~~ | **✅ Đã sửa.** `/affiliate/webhook` yêu cầu chữ ký HMAC-SHA256 trên body gốc (`X-Affiliate-Signature`) hoặc bí mật dùng chung (`X-Webhook-Secret`). Thiếu `AFFILIATE_WEBHOOK_SECRET` → `503`, sai chữ ký → `401`. | `backend/app/core/webhook_security.py` | — |
| ~~B2~~ | **✅ Đã sửa.** `X-Zalo-Signature` nay được kiểm HMAC-SHA256 trên body gốc; sửa body sau khi ký cũng bị chặn. | `backend/app/api/webhooks.py` | — |
| ~~B3~~ | **✅ Đã sửa.** `/telegram/link/confirm` và `/telegram/generate-link` yêu cầu header `X-Bot-Secret` khớp `TELEGRAM_BOT_SECRET`. | `backend/app/api/telegram.py` | — |
| B4 | Đơn AccessTrade lưu ở `affiliate_orders` nhưng `GET /orders` chỉ đọc bảng `orders` → **ví có tiền mà dashboard không có đơn tương ứng**. | `backend/app/api/orders.py` vs `backend/app/services/accesstrade_service.py` | Người dùng không đối chiếu được |
| ~~B5~~ | **✅ Đã sửa.** `UserRead` nay trả `role`; tab "Báo cáo" tự ẩn với tài khoản không phải ADMIN, `403` vẫn là lớp chặn thật sự ở backend. | `backend/app/schemas/common.py` | — |

### 6.2 Sai lệch hợp đồng FE ↔ BE

| # | Vấn đề | Vị trí |
|---|---|---|
| ~~C1~~ | **✅ Đã sửa.** Có `POST /auth/refresh`; FE lưu refresh token và tự làm mới khi gặp `401` rồi gọi lại request, chỉ dọn phiên khi refresh cũng hỏng. | `backend/app/api/auth.py`, `lib/api.ts`, `app/components/auth-context.tsx` |
| ~~C2~~ | **✅ Đã sửa.** FE từng định nghĩa bộ lọc `"ALL" \| "PENDING" \| "APPROVED" \| "REJECTED" \| "REVERSED"` — `REJECTED` không tồn tại trong `CashbackStatus`, đồng thời thiếu `NONE` và `REVIEW`. Nay bộ lọc, nhãn và màu badge đều sinh từ `lib/status.ts`. | `lib/status.ts`, `app/dashboard/page.tsx` |
| ~~C3~~ | **✅ Đã sửa.** CORS đọc từ `CORS_ORIGINS` (danh sách phân tách bằng dấu phẩy). | `backend/app/core/config.py`, `backend/app/main.py` |
| ~~C4~~ | **✅ Đã sửa.** `Settings` nay nhận cả `MINIMUM_WITHDRAWAL_AMOUNT` lẫn `MIN_WITHDRAWAL_AMOUNT` qua `AliasChoices`; mặc định hạ về 30.000 cho khớp giao diện. | `backend/app/core/config.py` |
| ~~C5~~ | **✅ Đã sửa cả hai đầu.** FE chọn phương thức từ `lib/payout.ts`; BE ràng buộc `method` bằng enum `WithdrawalMethod` và bắt buộc `bank_code` khi chuyển khoản ngân hàng. | `app/withdrawals/page.tsx`, `backend/app/schemas/common.py` |
| ~~C6~~ | **✅ Đã sửa.** `reason` nhận qua body (`RejectWithdrawalRequest`), tối thiểu 3 ký tự. Duyệt/từ chối nay chặn thao tác lên yêu cầu đã ở trạng thái cuối (`409`) và ghi `audit_logs`. | `backend/app/api/admin.py` |
| C7 | `/auth/logout` vẫn không thu hồi token — access token còn hiệu lực tới khi hết hạn (tối đa 30 phút). Đã ghi chú rõ trong mã; muốn thu hồi thật thì cần danh sách đen (Redis). | `backend/app/api/auth.py` |
| C8 | `get_idempotency_key` được khai báo nhưng không endpoint nào dùng (webhook tự đọc header). | `backend/app/api/deps.py` |
| C9 | `/orders`, `/affiliate/links`, `/wallet/transactions` **không phân trang**; `/admin/*` giới hạn cứng 200/500 mà không báo cho FE biết dữ liệu đã bị cắt. | nhiều file |
| ~~C10~~ | **✅ Đã sửa.** Trang chủ từng tự triển khai lại luồng đăng nhập song song với `auth-form.tsx`. Nay chỉ còn một nguồn: `lib/api.ts` + `auth-context.tsx` + `auth-modal.tsx`. Hai file cũ `app/components/auth-form.tsx` và `site-header.tsx` đã thành mã chết, cần xoá. | `app/components/` |

### 6.3 Khoảng trống tính năng (BE có, FE chưa có)

| # | Endpoint đã có | Màn hình FE còn thiếu |
|---|---|---|
| ~~G1~~ | `POST /zalo/link`, `GET /zalo/status`, `DELETE /zalo/unlink` | **✅ Đã có** — khối "Nhận link ngay trong chat" trên `/dashboard` (`app/components/channel-links.tsx`), kèm đếm ngược hiệu lực token |
| G2 | `POST /affiliate/accesstrade/link` | Nút tạo link AccessTrade thật (FE hiện chỉ gọi provider mock) |
| ~~G3~~ | `GET /wallet/transactions` | **✅ Đã có** — mục "Lịch sử ví" trên `/dashboard` |
| ~~G4~~ | `GET /admin/users`, `/admin/orders`, `/admin/withdrawals`, `/admin/orders/attribution-review`, `/admin/summary`, duyệt/từ chối rút | **✅ Đã có** — `/admin` gồm 5 tab + dải số liệu tổng quan + nút duyệt/từ chối |
| G5 | `GET /orders/{id}` | Chi tiết đơn nay mở ngay tại chỗ trên `/dashboard` (bấm vào dòng đơn) từ dữ liệu đã có; endpoint `/orders/{id}` vẫn chưa được gọi |

### 6.4 Chất lượng / kỹ thuật

| # | Vấn đề | Vị trí |
|---|---|---|
| ~~Q1~~ | **✅ Đã sửa.** `app/admin/page.tsx` từng hỏng mã hoá (UTF-8 bị đọc nhầm cp1252/latin-1 rồi lưu lại) và có BOM. Đã giải mã ngược và lưu lại UTF-8 không BOM; 13 dòng tiếng Việt hiển thị đúng trở lại. | `app/admin/page.tsx` |
| Q2 | Endpoint thật `/affiliate/generate-link` vẫn dùng `MockAffiliateProvider` (link `mock-affiliate.local`), trong khi `ShopeeAffiliateProvider` toàn bộ là `NotImplementedError`. Mock đang chạy trên đường dẫn production. | `backend/app/api/affiliate.py`, `backend/app/providers/affiliate/shopee.py` |
| Q3 | `POST /admin/cashback-rates` nhận rồi bỏ qua giá trị, chỉ trả `CONFIG_ACCEPTED`. Không nên trình bày như một tính năng hoàn chỉnh cho ADMIN. | `backend/app/api/admin.py` |
| Q4 | `Base.metadata.create_all(bind=engine)` chạy lúc import — không dùng migration. Sửa schema trên môi trường đã có dữ liệu sẽ không được áp dụng. | `backend/app/main.py` |
| Q5 | Truy vấn kiểm tra trùng khi đăng ký dùng `or_(... if ... else False)` + `.one_or_none()` → có thể ném `MultipleResultsFound` khi email và phone trùng ở hai user khác nhau, trả `500` thay vì `409`. | `backend/app/api/auth.py` |
| Q6 | `Index("ix_zalo_accounts_one_active_per_user", "user_id", "status", unique=True)` khiến một user **không thể có 2 bản ghi `INACTIVE`** — hủy liên kết lần thứ hai sẽ vi phạm ràng buộc. Nên dùng partial unique index chỉ trên `status = 'ACTIVE'`. | `backend/app/models/entities.py` |
| Q7 | File nguồn rải rác ở thư mục gốc (`route.ts`, `shorten.ts`, `supabase.ts`, `index.mjs`, `shopee_link_handler.py`, `files/`, `mnt/`) trùng lặp với `app/` và `lib/`. | thư mục gốc |

---

### 6.5 Khoản nợ kỹ thuật mới phát sinh

| # | Vấn đề | Vị trí |
|---|---|---|
| N1 | **Sổ tài khoản nhận tiền chỉ nằm ở `localStorage`** (`bee_payout_accounts_v1_<userId>`). Đổi máy hoặc xoá dữ liệu trình duyệt là mất; không đồng bộ giữa web và bot. Cần bảng `payout_accounts` + endpoint CRUD ở backend. | `lib/payout.ts` |
| N2 | Cột `withdrawals.bank_code` / `bank_name` được thêm bằng `ALTER TABLE` thủ công trên SQLite dev. Môi trường Postgres đang chạy sẽ **không** tự có cột này vì dự án chưa dùng migration (điểm Q4). | `backend/app/models/entities.py` |
| N3 | Danh sách ngân hàng là hằng số cứng trong `lib/payout.ts`. Ngân hàng đổi tên/sáp nhập phải sửa code và deploy lại. | `lib/payout.ts` |
| N4 | Email gửi đồng bộ trong `BackgroundTasks` của tiến trình web. Đủ dùng ở quy mô hiện tại, nhưng gửi hỏng thì **không có retry** và cũng không lưu vết đã gửi hay chưa. Khi lượng người dùng tăng nên chuyển sang hàng đợi (Redis/Celery) kèm bảng `email_log`. | `backend/app/api/auth.py` |
| N5 | Chỉ có đúng một loại thư (chào mừng). Các mốc đáng báo khác — cashback được duyệt, lệnh rút được chi trả hoặc bị từ chối — chưa gửi thư nào. | `backend/app/services/email_service.py` |

---

## 7. Thứ tự xử lý đề xuất

Đã hoàn thành: ~~**B1**~~ ~~**B2**~~ ~~**B3**~~ (xác thực webhook/bot), ~~**B5**~~ (`role` trong `UserRead`), ~~**C1**~~ (`/auth/refresh`), ~~**C2**~~ (đồng bộ enum FE), ~~**C3**~~ (CORS theo môi trường), ~~**C4**~~ (alias mức rút tối thiểu), ~~**C5**~~ (enum `method` + bắt buộc ngân hàng), ~~**C6**~~ (`reason` qua body + audit), ~~**C10**~~ (gộp một nguồn auth), ~~**G1**~~ ~~**G3**~~ ~~**G4**~~ (màn hình liên kết kênh, lịch sử ví, quản trị), ~~**Q1**~~ (mã hoá trang admin).

Còn lại, theo thứ tự ưu tiên:

1. **N2, Q4** — đưa Alembic vào. Cột `bank_code`/`bank_name` mới chỉ tồn tại trên SQLite dev nhờ `ALTER TABLE` thủ công; môi trường Postgres sẽ thiếu cột.
2. **B4** — hợp nhất hai mô hình đơn hàng (`orders` vs `affiliate_orders`), hoặc bổ sung endpoint để `/dashboard` thấy được đơn AccessTrade.
3. **N1** — chuyển sổ tài khoản nhận tiền từ `localStorage` sang bảng backend.
4. **Q2** — thay `MockAffiliateProvider` bằng provider Shopee/AccessTrade thật.
5. **C9** — phân trang cho `/orders`, `/affiliate/links`, `/wallet/transactions`, `/admin/*`.
6. **C7** — danh sách đen token nếu cần đăng xuất tức thì.
7. **Q3, Q5, Q6, Q7, N3** — các khoản nợ nhỏ còn lại.
