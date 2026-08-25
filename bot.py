import logging
import os
import httpx

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from shopee_link_handler import SHOPEE_LINK_REGEX, handle_shopee_link


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BACKEND_API = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000/api/v1")
# Backend chỉ chấp nhận các lời gọi thay mặt người dùng khi có bí mật này.
# Phải trùng với TELEGRAM_BOT_SECRET trong backend/.env.
BOT_SECRET = os.getenv("TELEGRAM_BOT_SECRET", "")
BOT_HEADERS = {"X-Bot-Secret": BOT_SECRET}


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    if not context.args:
        await update.message.reply_text("Dùng: /link MÃ_LIÊN_KẾT")
        return
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{BACKEND_API}/telegram/link/confirm",
            json={"token": context.args[0], "telegram_user_id": str(update.effective_user.id)},
            headers=BOT_HEADERS,
        )
    if response.status_code in (401, 503) and not BOT_SECRET:
        await update.message.reply_text("Bot chưa được cấu hình TELEGRAM_BOT_SECRET, liên hệ quản trị viên.")
        return
    if response.is_success:
        await update.message.reply_text("Đã liên kết Telegram. Các link Shopee sau đây sẽ được ghi nhận cho tài khoản website của bạn.")
    else:
        await update.message.reply_text(response.json().get("detail", "Mã liên kết không hợp lệ hoặc đã hết hạn."))


async def start(update: Update, context) -> None:
    await update.message.reply_text(
        "Bot Shopee affiliate đã sẵn sàng.\n"
        "Gửi link Shopee để bot tra cứu sản phẩm và tạo link affiliate."
    )


async def help_command(update: Update, context) -> None:
    await update.message.reply_text(
        "Cách dùng:\n"
        "1. Gửi một link Shopee dạng shopee.vn, s.shopee.vn hoặc vn.shp.ee\n"
        "2. Bot sẽ tra thông tin sản phẩm và trả về nút lấy link affiliate.\n\n"
        "Lưu ý: cần cấu hình SHOPEE_AFFILIATE_ID để sinh link affiliate thật."
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(MessageHandler(filters.Regex(SHOPEE_LINK_REGEX), handle_shopee_link))

    logging.info("Telegram bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()