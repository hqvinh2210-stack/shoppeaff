import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, affiliate, auth, orders, telegram, users, wallet, webhooks, withdrawals, zalo
from app.core.config import get_settings
from app.core.database import Base, engine
from app.models import entities  # noqa: F401


def configure_logging() -> None:
    """
    Đưa log của `app.*` ra cùng nơi với log uvicorn.

    Không có bước này thì `logger.info`/`logger.warning` trong các service bị nuốt
    hoàn toàn — nghĩa là một email gửi hỏng sẽ không để lại dấu vết nào.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        app_logger.addHandler(handler)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Cashback Affiliate System",
        version="1.0.0",
        description="FastAPI backend for user_id-centric Shopee cashback affiliate attribution.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(zalo.router, prefix="/api/v1", tags=["zalo"])
    app.include_router(telegram.router, prefix="/api/v1", tags=["telegram"])
    app.include_router(affiliate.router, prefix="/api/v1/affiliate", tags=["affiliate"])
    app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
    app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
    app.include_router(wallet.router, prefix="/api/v1/wallet", tags=["wallet"])
    app.include_router(withdrawals.router, prefix="/api/v1/withdrawals", tags=["withdrawals"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


Base.metadata.create_all(bind=engine)
app = create_app()