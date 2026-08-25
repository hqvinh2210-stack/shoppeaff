import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class AccessTradeClient:
    def __init__(self, token: str, base_url: str = "https://api.accesstrade.vn/v1", timeout: float = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"},
        )

    def close(self) -> None:
        self.client.close()

    @staticmethod
    def _backoff_seconds(response: httpx.Response, attempt: int) -> float:
        """
        Thời gian chờ trước khi thử lại.

        AccessTrade giới hạn 10 request/phút, tính theo cửa sổ phút. Backoff kiểu
        1s → 2s là vô nghĩa với quota như vậy: cả ba lần thử đều rơi trong cùng
        một phút bị chặn rồi cùng thất bại. Với 429 phải chờ theo thang phút, và
        ưu tiên `Retry-After` nếu máy chủ có nói.
        """
        if response.status_code != 429:
            return float(2**attempt)
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 120.0)
            except ValueError:
                pass
        return min(15.0 * (attempt + 1), 60.0)

    def _get(self, path: str, params: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                response = self.client.get(path, params=params)
                logger.info("AccessTrade GET %s status=%s elapsed_ms=%s", path, response.status_code, int((time.monotonic() - started) * 1000))
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt + 1 < attempts:
                        time.sleep(self._backoff_seconds(response, attempt))
                        continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt + 1 == attempts:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("AccessTrade request failed")

    def create_tracking_link(self, campaign_id: str, urls: list[str], tracking_id: str, **tracking: str) -> dict[str, Any]:
        payload = {"campaign_id": campaign_id, "urls": urls, "sub1": tracking_id, **tracking}
        response = self.client.post("/product_link/create", json=payload)
        logger.info("AccessTrade POST /product_link/create status=%s", response.status_code)
        response.raise_for_status()
        return response.json()

    def iter_orders(self, since: str, until: str, **filters: Any) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            data = self._get("/order-list", {"since": since, "until": until, "page": page, **filters})
            records = data.get("data", data if isinstance(data, list) else [])
            if not records:
                return
            yield from records
            if len(records) < int(filters.get("limit", 30)):
                return
            page += 1

    def get_order_products(self, order_id: str, merchant: str) -> dict[str, Any]:
        return self._get("/order-products", {"order_id": order_id, "merchant": merchant})

    def iter_transactions(self, since: str, until: str, **filters: Any) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            data = self._get("/transactions", {"since": since, "until": until, "page": page, **filters})
            records = data.get("data", data if isinstance(data, list) else [])
            if not records:
                return
            yield from records
            if len(records) < int(filters.get("limit", 30)):
                return
            page += 1