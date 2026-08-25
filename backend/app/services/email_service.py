"""
Gửi email giao dịch qua SMTP.

Nguyên tắc: **email không bao giờ được làm hỏng nghiệp vụ**. Máy chủ SMTP chậm
hay từ chối thì người dùng vẫn phải đăng ký thành công — lỗi chỉ được ghi log.
Vì vậy mọi lời gọi ở đây đều nuốt exception và trả về bool.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def send(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        """
        Gửi một email đa phần (plain text + HTML).

        Trả False khi chưa cấu hình SMTP hoặc gửi lỗi; không ném exception ra
        ngoài để nơi gọi không phải bọc try/except.
        """
        if not to_email:
            return False
        if not self.settings.email_enabled:
            logger.info("Bỏ qua gửi email tới %s: SMTP chưa được cấu hình", to_email)
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr(
            (self.settings.smtp_from_name, self.settings.sender_address)
        )
        message["To"] = to_email
        # Bản text luôn được đặt trước, HTML là phần thay thế — client không đọc
        # được HTML vẫn thấy nội dung đầy đủ.
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        try:
            self._deliver(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("Không gửi được email tới %s: %s", to_email, exc)
            return False

        logger.info("Đã gửi email '%s' tới %s", subject, to_email)
        return True

    def _deliver(self, message: EmailMessage) -> None:
        settings = self.settings
        # Cổng 465 dùng SSL ngay từ đầu; 587 kết nối thường rồi nâng cấp STARTTLS.
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            ) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
            return

        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
        ) as server:
            server.ehlo()
            if settings.smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)

    # ------------------------------------------------------------------ #
    # Các loại email cụ thể                                              #
    # ------------------------------------------------------------------ #

    def send_welcome(self, to_email: str, full_name: str | None, user_code: str) -> bool:
        """Thư chào mừng ngay sau khi tạo tài khoản thành công."""
        name = (full_name or "").strip() or "bạn"
        subject = "Chào mừng bạn đến với Bee Hoàn Tiền 🐝"
        return self.send(
            to_email,
            subject,
            _welcome_text(name, user_code, self.settings.app_base_url),
            _welcome_html(name, user_code, self.settings.app_base_url),
        )


def _welcome_text(name: str, user_code: str, base_url: str) -> str:
    return f"""Xin chào {name},

Tài khoản Bee Hoàn Tiền của bạn đã được tạo thành công.

Mã tài khoản của bạn: {user_code}

Ba bước để bắt đầu nhận tiền hoàn:
1. Dán link sản phẩm Shopee vào trang Tổng quan để tạo link tracking riêng.
2. Mua sắm qua chính link đó, hoặc chia sẻ cho bạn bè.
3. Đơn được ghi nhận, tiền hoàn vào ví và rút về ngân hàng từ 30.000d.

Mở trang Tổng quan: {base_url}/dashboard

Mẹo: liên kết tài khoản với bot Telegram hoặc Zalo để gửi link Shopee
thẳng trong khung chat, đơn vẫn ghi nhận về đúng tài khoản này.

--
Bee Hoàn Tiền
Email này được gửi tự động, vui lòng không trả lời.
"""


def _welcome_html(name: str, user_code: str, base_url: str) -> str:
    """
    HTML dùng bảng và style nội tuyến — client email (Gmail, Outlook) bỏ qua
    thẻ <style>, flexbox và biến CSS, nên không dùng những thứ đó ở đây.
    Bảng màu lấy từ giao diện web để email nhìn cùng một thương hiệu.
    """
    return f"""<!doctype html>
<html lang="vi">
<body style="margin:0;padding:24px 12px;background:#fff7df;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#241607;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:560px;margin:0 auto;">
    <tr>
      <td style="padding:0 0 20px;">
        <span style="display:inline-block;width:40px;height:40px;line-height:40px;text-align:center;border-radius:13px;background:#ffc928;font-size:21px;">&#128029;</span>
        <strong style="font-size:19px;letter-spacing:-.03em;vertical-align:middle;margin-left:9px;">Bee Hoàn Tiền</strong>
      </td>
    </tr>
    <tr>
      <td style="padding:28px;border-radius:22px;background:#fffaf0;border:1px solid rgba(91,59,8,.14);">
        <p style="margin:0 0 6px;font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#9b6a00;">Tài khoản đã sẵn sàng</p>
        <h1 style="margin:0 0 16px;font-size:28px;line-height:1.15;letter-spacing:-.04em;">Xin chào {name}!</h1>
        <p style="margin:0 0 20px;font-size:15px;line-height:1.7;color:#62451c;">
          Tài khoản Bee Hoàn Tiền của bạn đã được tạo thành công. Từ giờ mỗi link
          Shopee bạn tạo đều gắn mã tracking riêng, và tiền hoàn sẽ về thẳng ví của bạn.
        </p>

        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 22px;">
          <tr>
            <td style="padding:14px 16px;border-radius:14px;background:#f7df9d;">
              <span style="font-size:13px;color:#6d4500;">Mã tài khoản của bạn</span><br>
              <strong style="font-size:19px;letter-spacing:.04em;">{user_code}</strong>
            </td>
          </tr>
        </table>

        <p style="margin:0 0 10px;font-weight:800;font-size:15px;">Ba bước để bắt đầu</p>
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin:0 0 24px;">
          <tr><td style="padding:8px 0;font-size:14px;line-height:1.6;color:#684b20;"><strong style="color:#9b6a00;">01</strong> &nbsp; Dán link sản phẩm Shopee để tạo link tracking riêng.</td></tr>
          <tr><td style="padding:8px 0;font-size:14px;line-height:1.6;color:#684b20;"><strong style="color:#9b6a00;">02</strong> &nbsp; Mua sắm qua chính link đó, hoặc chia sẻ cho bạn bè.</td></tr>
          <tr><td style="padding:8px 0;font-size:14px;line-height:1.6;color:#684b20;"><strong style="color:#9b6a00;">03</strong> &nbsp; Đơn được ghi nhận, tiền hoàn vào ví, rút về ngân hàng từ 30.000&#8363;.</td></tr>
        </table>

        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
          <tr>
            <td style="border-radius:14px;background:#241607;">
              <a href="{base_url}/dashboard" style="display:inline-block;padding:14px 26px;color:#fff7df;text-decoration:none;font-weight:800;font-size:15px;">Mở trang Tổng quan</a>
            </td>
          </tr>
        </table>

        <p style="margin:24px 0 0;padding:14px 16px;border-radius:14px;background:rgba(255,201,40,.24);font-size:13px;line-height:1.65;color:#6d4500;">
          <strong>Mẹo:</strong> liên kết tài khoản với bot Telegram hoặc Zalo để gửi link
          Shopee thẳng trong khung chat — đơn vẫn ghi nhận về đúng tài khoản này.
        </p>
      </td>
    </tr>
    <tr>
      <td style="padding:20px 4px;font-size:12px;line-height:1.6;color:#8a7350;">
        Email này được gửi tự động, vui lòng không trả lời.<br>
        &copy; 2026 Bee Hoàn Tiền
      </td>
    </tr>
  </table>
</body>
</html>"""
