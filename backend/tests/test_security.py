"""
Kiểm tra lớp xác thực của webhook và bot.

Các endpoint này ghi thẳng vào ví người dùng nên phải fail closed: thiếu cấu
hình bí mật thì trả 503, sai chữ ký thì 401, không bao giờ cho đi qua.
"""

import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.core.webhook_security import (
    compute_signature,
    verify_shared_secret,
    verify_signature,
)

SECRET = "test-secret"
BODY = b'{"orders":[]}'


def expected(body: bytes = BODY, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_compute_signature_matches_hmac_sha256():
    assert compute_signature(BODY, SECRET) == expected()


def test_verify_signature_accepts_valid_signature():
    verify_signature(BODY, expected(), SECRET, "Test")


def test_verify_signature_accepts_sha256_prefix():
    """Nhiều nhà cung cấp gửi dạng `sha256=<hex>`."""
    verify_signature(BODY, f"sha256={expected()}", SECRET, "Test")


def test_verify_signature_rejects_missing_signature():
    with pytest.raises(HTTPException) as caught:
        verify_signature(BODY, None, SECRET, "Test")
    assert caught.value.status_code == 401


def test_verify_signature_rejects_wrong_signature():
    with pytest.raises(HTTPException) as caught:
        verify_signature(BODY, "deadbeef", SECRET, "Test")
    assert caught.value.status_code == 401


def test_verify_signature_rejects_tampered_body():
    """Chữ ký đúng với body cũ không được dùng lại cho body đã sửa."""
    with pytest.raises(HTTPException) as caught:
        verify_signature(b'{"orders":[{"amount":999}]}', expected(), SECRET, "Test")
    assert caught.value.status_code == 401


def test_missing_secret_fails_closed_with_503():
    with pytest.raises(HTTPException) as caught:
        verify_signature(BODY, expected(), None, "Test")
    assert caught.value.status_code == 503

    with pytest.raises(HTTPException) as caught:
        verify_shared_secret(SECRET, None, "Test")
    assert caught.value.status_code == 503


def test_verify_shared_secret_round_trip():
    verify_shared_secret(SECRET, SECRET, "Test")
    for wrong in (None, "", "sai-bi-mat"):
        with pytest.raises(HTTPException) as caught:
            verify_shared_secret(wrong, SECRET, "Test")
        assert caught.value.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token():
    """Hai loại token ký bằng khoá khác nhau nên không thể dùng thay nhau."""
    from app.core.security import (
        create_access_token,
        create_refresh_token,
        decode_access_token,
        decode_refresh_token,
    )

    access = create_access_token("1")
    refresh = create_refresh_token("1")

    assert decode_access_token(access)["sub"] == "1"
    assert decode_refresh_token(refresh)["sub"] == "1"

    with pytest.raises(ValueError):
        decode_access_token(refresh)
    with pytest.raises(ValueError):
        decode_refresh_token(access)


def test_cors_origins_parse_from_comma_separated_string():
    from app.core.config import Settings

    settings = Settings(_env_file=None, CORS_ORIGINS="https://a.vn, https://b.vn ,")
    assert settings.cors_origin_list == ["https://a.vn", "https://b.vn"]
