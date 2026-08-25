# Zalo Shopee Affiliate Bot (zca-js)

Bot Zalo cá nhân: dán link Shopee vào chat → bot trả thông tin sản phẩm + breakdown hoa hồng + link affiliate.

⚠️ Dùng thư viện KHÔNG chính thức (zca-js, giả lập Zalo Web). Vi phạm điều khoản Zalo có thể bị khoá/hạn chế tài khoản — nên test bằng tài khoản phụ, không spam / gọi tần suất cao.

## Cài đặt

```bash
npm install
```

## Chạy

```bash
SHOPEE_AFFILIATE_ID=xxxx node index.mjs
```

Quét mã QR hiện ra bằng app Zalo trên điện thoại của tài khoản muốn dùng làm bot. Sau khi login, bot tự lắng nghe tin nhắn trong cả chat riêng lẫn nhóm.

## Biến môi trường

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `SHOPEE_AFFILIATE_ID` | Có | affiliate_id của bạn để sinh link affiliate |
| `SHOPEE_BASE_RATE` | Không | % hoa hồng sàn cơ bản tài khoản bạn (vd `8`) |
| `SHOPEE_CAP` | Không | Trần hoa hồng sàn VNĐ (vd `20000`) |
| `SHOPEE_SUBID_PUBLISHER` | Không | Tên publisher gắn vào sub_id, mặc định `zalobot` |
| `ZALO_ONLY_GROUPS` | Không | Set `1` để bot chỉ trả lời trong nhóm, bỏ qua chat riêng |
