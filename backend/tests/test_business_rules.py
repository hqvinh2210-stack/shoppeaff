from decimal import Decimal

import pytest

from app.models.entities import AffiliateClick, AffiliateLink, AffiliateOrder, AffiliateTransaction, CashbackTransaction, Order, UnmatchedAffiliateOrder, User, Wallet, Withdrawal
from app.models.enums import CashbackStatus, CommissionStatus, OrderStatus, WithdrawalStatus
from app.providers.affiliate.base import AffiliateOrderPayload
from app.services.affiliate_service import AffiliateService
from app.services.order_service import OrderService
from app.services.wallet_service import WalletService
from app.services.withdrawal_service import WithdrawalService
from app.services.zalo_service import ZaloService
from app.utils.tracking import build_tracking_id, parse_tracking_id
from app.services.accesstrade_service import AccessTradeService
from app.services.cashback_reconciliation import CashbackReconciliationService


class FakeAccessTradeClient:
    def create_tracking_link(self, campaign_id, urls, tracking_id, **tracking):
        self.payload = {"campaign_id": campaign_id, "urls": urls, "sub1": tracking_id, **tracking}
        return {"success": True, "data": {"success_link": [{"aff_link": "https://at.test/a", "short_link": "https://at.test/s", "url_origin": urls[0]}]}}


def test_tracking_id_round_trip():
    tracking_id = build_tracking_id(user_id=10001, affiliate_link_id=50001)

    assert tracking_id == "CB_10001_50001"
    assert parse_tracking_id(tracking_id) == (10001, 50001)


def test_accesstrade_click_uses_random_tracking_and_sub1(db_session):
    user = User(user_code="USR_AT_1", email="at1@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    client = FakeAccessTradeClient()

    click = AccessTradeService(db_session, client).create_click(user.id, "CAMPAIGN_1", "https://shopee.vn/product/1")

    assert click.tracking_id.startswith("trk_")
    assert click.sub1 == click.tracking_id
    assert client.payload["sub1"] == click.tracking_id
    assert click.status == "CREATED"


def test_accesstrade_unmatched_order_is_saved_once(db_session):
    service = AccessTradeService(db_session, FakeAccessTradeClient())
    record = {"order_id": "AT-1", "merchant": "Shopee", "status": 0, "at_product_link": "https://shopee.vn/product/1"}

    first = service.upsert_order(record)
    service.upsert_order(record)

    assert first.user_id is None
    assert db_session.query(AffiliateOrder).count() == 1
    assert db_session.query(UnmatchedAffiliateOrder).count() == 1


def test_accesstrade_cashback_reconciles_and_reverses(db_session):
    user = User(user_code="USR_AT_2", email="at2@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    click = AffiliateClick(user_id=user.id, tracking_id="trk_cashback_1", campaign_id="CAMPAIGN_1", product_url="https://shopee.vn/product/1", sub1="trk_cashback_1")
    transaction = AffiliateTransaction(network="ACCESSTRADE", merchant="Shopee", transaction_id="AT-TX-1", product_id="P-1", user_id=user.id, tracking_id=click.tracking_id, commission=Decimal("30000"), status=0, is_confirmed=0, raw_data={"status": 0})
    db_session.add_all([click, transaction])
    db_session.commit()
    service = CashbackReconciliationService(db_session, Decimal("70"))

    pending = service.process_transaction(transaction)
    transaction.status = 1
    transaction.is_confirmed = 1
    approved = service.process_transaction(transaction)
    transaction.status = 2
    reversed_tx = service.process_transaction(transaction)

    assert pending.transaction_type == "CASHBACK_PENDING"
    assert approved.transaction_type == "CASHBACK_APPROVED"
    assert reversed_tx.transaction_type == "CASHBACK_REVERSED"
    assert db_session.query(CashbackTransaction).filter_by(affiliate_transaction_id=transaction.id).count() == 3


def test_zalo_account_linking(db_session):
    user = User(user_code="USR_10001", email="u@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    service = ZaloService(db_session)
    link_token = service.create_link_token(user.id)
    db_session.commit()

    linked = service.link_account(token=link_token.token, zalo_user_id="ZALO_ABC")

    assert linked.user_id == user.id
    assert linked.zalo_user_id == "ZALO_ABC"
    assert link_token.status == "USED"

def test_zalo_user_id_resolution(db_session):
    user = User(user_code="USR_10001", email="u@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    service = ZaloService(db_session)
    link_token = service.create_link_token(user.id)
    db_session.commit()
    service.link_account(token=link_token.token, zalo_user_id="ZALO_ABC")
    db_session.commit()

    resolved_user_id = service.resolve_user_id("ZALO_ABC")
    assert resolved_user_id == user.id

    assert service.resolve_user_id("NON_EXISTENT_ZALO_ID") is None


def test_affiliate_link_generation_uses_user_tracking_id(db_session, mock_affiliate_provider):
    user = User(user_code="USR_10002", email="u2@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    service = AffiliateService(db_session, mock_affiliate_provider)
    link = service.generate_link(user.id, "https://shopee.vn/product/123")

    assert link.user_id == user.id
    assert link.tracking_id == f"CB_{user.id}_{link.id}"
    assert link.affiliate_url.endswith(f"sub_id={link.tracking_id}")


def test_order_attribution_creates_pending_cashback(db_session):
    user = User(user_code="USR_10003", email="u3@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    link = AffiliateLink(
        user_id=user.id,
        original_url="https://shopee.vn/product/123",
        normalized_url="https://shopee.vn/product/123",
        affiliate_url="https://affiliate.test/x",
        tracking_id="CB_PLACEHOLDER",
        platform="shopee",
        status="ACTIVE",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)

    link.tracking_id = build_tracking_id(user.id, link.id)
    db_session.commit()

    service = OrderService(db_session, cashback_rate_percent=Decimal("70"))
    order = service.upsert_order_from_affiliate(
        AffiliateOrderPayload(
            platform="shopee",
            platform_order_id="SP123456",
            tracking_id=link.tracking_id,
            product_id="123",
            product_name="Test Product",
            order_amount=Decimal("100000"),
            commission_amount=Decimal("50000"),
            currency="VND",
            order_status=OrderStatus.PENDING.value,
            commission_status=CommissionStatus.PENDING.value,
        )
    )

    assert order.user_id == user.id
    assert order.affiliate_link_id == link.id
    assert order.cashback_amount == Decimal("35000.00")
    assert order.cashback_status == CashbackStatus.PENDING.value


def test_unmatched_order_goes_to_attribution_review(db_session):
    service = OrderService(db_session, cashback_rate_percent=Decimal("70"))

    order = service.upsert_order_from_affiliate(
        AffiliateOrderPayload(
            platform="shopee",
            platform_order_id="SP_UNMATCHED",
            tracking_id="UNKNOWN",
            product_id="UNKNOWN_PROD",
            product_name="Unknown Product",
            order_amount=Decimal("0"),
            commission_amount=Decimal("50000"),
            currency="VND",
            order_status=OrderStatus.ATTRIBUTION_REVIEW.value,
            commission_status=CommissionStatus.PENDING.value,
        )
    )

    assert order.user_id is None
    assert order.order_status == OrderStatus.ATTRIBUTION_REVIEW.value
    assert order.cashback_status == CashbackStatus.REVIEW.value


def test_duplicate_order_updates_without_duplicate_cashback(db_session):
    service = OrderService(db_session, cashback_rate_percent=Decimal("70"))

    first = service.upsert_order_from_affiliate(
        AffiliateOrderPayload(
            platform="shopee",
            platform_order_id="SP_DUP",
            tracking_id="UNKNOWN",
            product_id="DUP_PROD",
            product_name="Duplicate Product",
            order_amount=Decimal("100000"),
            commission_amount=Decimal("50000"),
            currency="VND",
            order_status=OrderStatus.PENDING.value,
            commission_status=CommissionStatus.PENDING.value,
        )
    )
    second = service.upsert_order_from_affiliate(
        AffiliateOrderPayload(
            platform="shopee",
            platform_order_id="SP_DUP",
            tracking_id="UNKNOWN",
            product_id="DUP_PROD",
            product_name="Duplicate Product",
            order_amount=Decimal("120000"),
            commission_amount=Decimal("60000"),
            currency="VND",
            order_status=OrderStatus.PENDING.value,
            commission_status=CommissionStatus.PENDING.value,
        )
    )

    assert first.id == second.id
    assert db_session.query(Order).filter_by(platform_order_id="SP_DUP").count() == 1


def test_settled_completed_order_is_pending_until_worker_approval(db_session):
    user = User(user_code="USR_10007", email="u7@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    link = AffiliateLink(
        user_id=user.id,
        original_url="https://shopee.vn/product/123",
        normalized_url="https://shopee.vn/product/123",
        affiliate_url="https://affiliate.test/x",
        tracking_id="CB_10007_1",
        platform="shopee",
        status="ACTIVE",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    link.tracking_id = build_tracking_id(user.id, link.id)
    db_session.commit()

    order = OrderService(db_session, Decimal("70")).upsert_order_from_affiliate(
        AffiliateOrderPayload(
            platform="shopee",
            platform_order_id="SP_SETTLED",
            tracking_id=link.tracking_id,
            product_id="123",
            product_name="Settled Product",
            order_amount=Decimal("100000"),
            commission_amount=Decimal("50000"),
            currency="VND",
            order_status=OrderStatus.COMPLETED.value,
            commission_status=CommissionStatus.SETTLED.value,
        )
    )

    assert order.cashback_status == CashbackStatus.PENDING.value
    assert WalletService(db_session).approve_cashback(user.id, order.id, order.cashback_amount).amount == Decimal("35000.00")


def test_cashback_approval_is_idempotent(db_session):
    user = User(user_code="USR_10008", email="u8@example.com", status="ACTIVE")
    wallet = Wallet(user=user, available_balance=Decimal("0"), pending_balance=Decimal("35000"))
    order = Order(
        user=user,
        platform="shopee",
        platform_order_id="SP_APPROVE_ONCE",
        commission_amount=Decimal("50000"),
        cashback_rate=Decimal("70"),
        cashback_amount=Decimal("35000"),
        currency="VND",
        order_status=OrderStatus.COMPLETED.value,
        commission_status=CommissionStatus.SETTLED.value,
        cashback_status=CashbackStatus.PENDING.value,
    )
    db_session.add_all([wallet, order])
    db_session.commit()
    db_session.refresh(order)
    service = WalletService(db_session)

    first = service.approve_cashback(user.id, order.id, Decimal("35000"))
    second = service.approve_cashback(user.id, order.id, Decimal("35000"))

    assert first.id == second.id
    assert wallet.available_balance == Decimal("35000")
    assert db_session.query(CashbackTransaction).filter_by(order_id=order.id).count() == 1


def test_wallet_approval_creates_immutable_transaction(db_session):
    user = User(user_code="USR_10004", email="u4@example.com", status="ACTIVE")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    wallet = Wallet(user_id=user.id, available_balance=Decimal("0"), pending_balance=Decimal("35000"))
    order = Order(
        user_id=user.id,
        platform="shopee",
        platform_order_id="SP_WALLET",
        commission_amount=Decimal("50000"),
        cashback_rate=Decimal("70"),
        cashback_amount=Decimal("35000"),
        currency="VND",
        order_status=OrderStatus.COMPLETED.value,
        commission_status=CommissionStatus.SETTLED.value,
        cashback_status=CashbackStatus.PENDING.value,
    )
    db_session.add_all([wallet, order])
    db_session.commit()
    db_session.refresh(order)

    transaction = WalletService(db_session).approve_cashback(user_id=order.user_id, order_id=order.id, amount=order.cashback_amount)

    assert transaction.amount == Decimal("35000")
    assert transaction.balance_before == Decimal("0")
    assert transaction.balance_after == Decimal("35000")
    assert wallet.available_balance == Decimal("35000")
    assert wallet.pending_balance == Decimal("0")
    assert order.cashback_status == CashbackStatus.APPROVED.value


def test_withdrawal_rejects_amount_above_available_balance(db_session):
    user = User(user_code="USR_10005", email="u5@example.com", status="ACTIVE")
    wallet = Wallet(user=user, available_balance=Decimal("30000"), pending_balance=Decimal("0"))
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(user)

    # Thông điệp lỗi được hiển thị thẳng cho người dùng qua `detail` nên viết tiếng Việt.
    with pytest.raises(ValueError, match="vượt quá số dư khả dụng"):
        WithdrawalService(db_session, min_withdrawal_amount=Decimal("10000")).request_withdrawal(
            user_id=user.id,
            amount=Decimal("50000"),
            method="BANK",
            bank_code="VCB",
            account_name="NGUYEN VAN A",
            account_number="123456789",
        )


def test_withdrawal_creates_pending_request(db_session):
    user = User(user_code="USR_10006", email="u6@example.com", status="ACTIVE")
    wallet = Wallet(user=user, available_balance=Decimal("100000"), pending_balance=Decimal("0"))
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(user)

    withdrawal = WithdrawalService(db_session, min_withdrawal_amount=Decimal("50000")).request_withdrawal(
        user_id=user.id,
        amount=Decimal("50000"),
        method="BANK",
        account_name="Nguyen Van A",
        account_number="123456789",
    )

    assert isinstance(withdrawal, Withdrawal)
    assert withdrawal.status == WithdrawalStatus.PENDING.value


def test_rejected_withdrawal_restores_reserved_balance(db_session):
    user = User(user_code="USR_10009", email="u9@example.com", status="ACTIVE")
    wallet = Wallet(user=user, available_balance=Decimal("100000"), pending_balance=Decimal("0"))
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(user)
    service = WithdrawalService(db_session, min_withdrawal_amount=Decimal("50000"))
    withdrawal = service.request_withdrawal(user.id, Decimal("50000"), "BANK", "Nguyen Van A", "123456789")
    service.reject_withdrawal(withdrawal, "Invalid account")

    assert withdrawal.status == WithdrawalStatus.REJECTED.value
    assert wallet.available_balance == Decimal("100000")

def test_withdrawal_request_requires_bank_for_bank_transfer():
    """Chuyển khoản ngân hàng phải kèm ngân hàng nhận; ví điện tử thì không."""
    from pydantic import ValidationError

    from app.schemas.common import WithdrawalCreateRequest

    with pytest.raises(ValidationError, match="bắt buộc chọn ngân hàng nhận"):
        WithdrawalCreateRequest(
            amount=Decimal("30000"),
            method="BANK",
            account_name="NGUYEN VAN A",
            account_number="123456789",
        )

    wallet_request = WithdrawalCreateRequest(
        amount=Decimal("30000"),
        method="MOMO",
        account_name="NGUYEN VAN A",
        account_number="0967913855",
    )
    assert wallet_request.bank_code is None


def test_withdrawal_request_rejects_unknown_method():
    from pydantic import ValidationError

    from app.schemas.common import WithdrawalCreateRequest

    with pytest.raises(ValidationError):
        WithdrawalCreateRequest(
            amount=Decimal("30000"),
            method="PAYPAL",
            account_name="NGUYEN VAN A",
            account_number="123456789",
        )
