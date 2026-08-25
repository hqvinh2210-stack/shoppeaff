"""
Xác thực các endpoint không dùng JWT: webhook của mạng affiliate và bot chat.

Nguyên tắc chung ở đây là **fail closed**: thiếu cấu hình bí mật thì endpoint
trả 503 chứ không cho đi qua. Trước đây `/affiliate/webhook` không kiểm gì và
`/webhooks/zalo` chỉ kiểm header có tồn tại hay không, nghĩa là bất kỳ ai cũng
tạo được đơn và cộng được tiền hoàn.
"""

import hashlib
import hmac

from fastapi import HTTPException, status


def _require_secret(secret: str | None, feature: str) -> str:
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{feature} chưa được cấu hình bí mật xác thực",
        )
    return secret


def verify_shared_secret(
    provided: str | None,
    expected: str | None,
    feature: str,
) -> None:
    """So khớp bí mật dùng chung (dạng header tĩnh) theo thời gian hằng số."""
    secret = _require_secret(expected, feature)
    if not provided or not hmac.compare_digest(provided, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{feature}: bí mật xác thực không hợp lệ",
        )


def compute_signature(body: bytes, secret: str) -> str:
    """HMAC-SHA256 của nguyên văn thân request, viết dạng hex thường."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(
    body: bytes,
    provided: str | None,
    expected_secret: str | None,
    feature: str,
) -> None:
    """
    Kiểm chữ ký HMAC trên nguyên văn body.

    Phải ký trên **bytes gốc** chứ không phải JSON đã parse lại: thứ tự khoá và
    khoảng trắng thay đổi sẽ làm chữ ký lệch dù nội dung y hệt.
    """
    secret = _require_secret(expected_secret, feature)
    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{feature}: thiếu chữ ký",
        )
    # Chấp nhận cả dạng "sha256=<hex>" mà nhiều nhà cung cấp dùng.
    candidate = provided.split("=", 1)[1] if provided.startswith("sha256=") else provided
    if not hmac.compare_digest(candidate.lower(), compute_signature(body, secret)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{feature}: chữ ký không hợp lệ",
        )
