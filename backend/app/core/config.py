from functools import lru_cache
from decimal import Decimal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    domain: str = Field(default="localhost", alias="DOMAIN")

    # Danh sách origin của frontend, phân tách bằng dấu phẩy. Không hardcode
    # localhost trong mã nguồn nữa để triển khai được ra domain thật.
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    database_url: str = Field(default="sqlite:///./cashback_dev.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    jwt_secret: str = Field(default="change-me-access-secret", alias="JWT_SECRET")
    jwt_refresh_secret: str = Field(default="change-me-refresh-secret", alias="JWT_REFRESH_SECRET")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    zalo_app_id: str | None = Field(default=None, alias="ZALO_APP_ID")
    zalo_app_secret: str | None = Field(default=None, alias="ZALO_APP_SECRET")
    zalo_oa_access_token: str | None = Field(default=None, alias="ZALO_OA_ACCESS_TOKEN")
    zalo_webhook_secret: str | None = Field(default=None, alias="ZALO_WEBHOOK_SECRET")

    # Bí mật dùng ký/kiểm webhook và xác thực bot. Thiếu cấu hình thì endpoint
    # tương ứng trả 503 chứ không mở cửa — fail closed, không fail open.
    affiliate_webhook_secret: str | None = Field(default=None, alias="AFFILIATE_WEBHOOK_SECRET")
    telegram_bot_secret: str | None = Field(default=None, alias="TELEGRAM_BOT_SECRET")

    affiliate_api_key: str | None = Field(default=None, alias="AFFILIATE_API_KEY")
    affiliate_api_secret: str | None = Field(default=None, alias="AFFILIATE_API_SECRET")
    accesstrade_api_token: str | None = Field(default=None, alias="ACCESSTRADE_API_TOKEN")
    accesstrade_campaign_id: str | None = Field(default=None, alias="ACCESSTRADE_CAMPAIGN_ID")
    accesstrade_base_url: str = Field(default="https://api.accesstrade.vn/v1", alias="ACCESSTRADE_BASE_URL")
    accesstrade_timeout_seconds: float = Field(default=10, alias="ACCESSTRADE_TIMEOUT_SECONDS")

    # ----- Gửi email (SMTP) -----
    # Thiếu host/username/password thì hệ thống bỏ qua việc gửi mail và ghi log,
    # không bao giờ để lỗi SMTP làm hỏng luồng đăng ký.
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field(default="Bee Hoàn Tiền", alias="SMTP_FROM_NAME")
    smtp_timeout_seconds: float = Field(default=15, alias="SMTP_TIMEOUT_SECONDS")

    # Dùng dựng link trong nội dung email.
    app_base_url: str = Field(default="http://localhost:3000", alias="APP_BASE_URL")

    cashback_rate_percent: Decimal = Field(default=Decimal("70.00"), alias="CASHBACK_RATE_PERCENT")
    minimum_withdrawal_amount: Decimal = Field(
        default=Decimal("30000"),
        validation_alias=AliasChoices("MINIMUM_WITHDRAWAL_AMOUNT", "MIN_WITHDRAWAL_AMOUNT"),
    )
    currency: str = Field(default="VND", alias="CURRENCY")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)

    @property
    def sender_address(self) -> str:
        """Địa chỉ hiển thị ở ô From; Gmail bắt buộc trùng tài khoản đăng nhập."""
        return self.smtp_from_email or self.smtp_username or ""


@lru_cache
def get_settings() -> Settings:
    return Settings()