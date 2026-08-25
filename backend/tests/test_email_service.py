"""
Kiểm tra dịch vụ email.

Trọng tâm là hai điều: nội dung thư đúng, và **lỗi SMTP không bao giờ được lan
ra ngoài** — người dùng phải đăng ký thành công kể cả khi máy chủ mail chết.
"""

import smtplib
from email.message import EmailMessage

import pytest

from app.core.config import Settings
from app.services.email_service import EmailService


def configured(**overrides) -> Settings:
    """
    Dựng Settings độc lập với `.env` của máy đang chạy test.

    Không có `_env_file=None`, pydantic-settings sẽ nạp `backend/.env` thật và
    test đỗ hay trượt tuỳ theo máy của từng người.
    """
    values = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": 587,
        "SMTP_USERNAME": "bot@example.com",
        "SMTP_PASSWORD": "secret",
        "APP_BASE_URL": "https://bee.test",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_email_disabled_when_smtp_incomplete():
    assert Settings(_env_file=None, SMTP_HOST="smtp.example.com").email_enabled is False
    assert configured().email_enabled is True


def test_sender_falls_back_to_username():
    assert configured().sender_address == "bot@example.com"
    assert configured(SMTP_FROM_EMAIL="no-reply@bee.vn").sender_address == "no-reply@bee.vn"


def test_send_is_skipped_when_not_configured(monkeypatch):
    """Chưa cấu hình SMTP thì im lặng bỏ qua, không được ném lỗi."""
    service = EmailService(Settings(_env_file=None))
    called = False

    def fail(_message):
        nonlocal called
        called = True

    monkeypatch.setattr(service, "_deliver", fail)
    assert service.send_welcome("ai@example.com", "A", "USR_1") is False
    assert called is False


def test_send_is_skipped_for_empty_recipient():
    assert EmailService(configured()).send_welcome("", "A", "USR_1") is False


def test_welcome_email_content(monkeypatch):
    service = EmailService(configured())
    captured: list[EmailMessage] = []
    monkeypatch.setattr(service, "_deliver", captured.append)

    assert service.send_welcome("nguoidung@example.com", "Lê Thị Hoa", "USR_42") is True

    message = captured[0]
    assert message["To"] == "nguoidung@example.com"
    assert "Bee Hoàn Tiền" in message["Subject"]
    assert "bot@example.com" in message["From"]

    bodies = [part.get_content() for part in message.walk() if part.get_content_type().startswith("text/")]
    joined = "\n".join(bodies)
    assert "Lê Thị Hoa" in joined
    assert "USR_42" in joined
    # Link trong thư phải trỏ về APP_BASE_URL đã cấu hình, không hardcode localhost.
    assert "https://bee.test/dashboard" in joined

    subtypes = {part.get_content_subtype() for part in message.walk() if part.get_content_type().startswith("text/")}
    assert subtypes == {"plain", "html"}


def test_missing_full_name_falls_back_politely(monkeypatch):
    service = EmailService(configured())
    captured: list[EmailMessage] = []
    monkeypatch.setattr(service, "_deliver", captured.append)

    service.send_welcome("nguoidung@example.com", None, "USR_7")

    plain = next(
        part.get_content()
        for part in captured[0].walk()
        if part.get_content_type() == "text/plain"
    )
    assert "Xin chào bạn," in plain


@pytest.mark.parametrize(
    "error",
    [smtplib.SMTPAuthenticationError(535, b"bad password"), OSError("mạng hỏng")],
)
def test_smtp_failure_never_propagates(monkeypatch, error):
    """Sai mật khẩu ứng dụng hay mất mạng đều chỉ làm hàm trả False."""
    service = EmailService(configured())

    def boom(_message):
        raise error

    monkeypatch.setattr(service, "_deliver", boom)
    assert service.send_welcome("nguoidung@example.com", "A", "USR_1") is False
