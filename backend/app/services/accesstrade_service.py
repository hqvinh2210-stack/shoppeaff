import json
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.models.entities import AffiliateClick, AffiliateOrder, AffiliateTransaction, UnmatchedAffiliateOrder
from app.providers.affiliate.accesstrade import AccessTradeClient


def new_tracking_id() -> str:
    return f"trk_{uuid.uuid4().hex}"


def _number(value: Any) -> Decimal | None:
    if value is None or isinstance(value, dict):
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None


def _tracking_value(record: dict[str, Any]) -> str | None:
    for key in ("sub1", "tracking_id"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    for key in ("at_product_link", "click_url"):
        value = record.get(key)
        if isinstance(value, str):
            query = parse_qs(urlparse(value).query)
            if query.get("sub1"):
                return query["sub1"][0]
    extra = record.get("_extra")
    if isinstance(extra, dict):
        parameters = extra.get("parameters")
        if isinstance(parameters, dict) and isinstance(parameters.get("sub1"), str):
            return parameters["sub1"]
    return None


class AccessTradeService:
    def __init__(self, db: Session, client: AccessTradeClient):
        self.db = db
        self.client = client

    def create_click(self, user_id: int, campaign_id: str, product_url: str, merchant: str | None = None) -> AffiliateClick:
        tracking_id = new_tracking_id()
        click = AffiliateClick(
            user_id=user_id, tracking_id=tracking_id, campaign_id=campaign_id,
            merchant=merchant, product_url=product_url, sub1=tracking_id,
        )
        self.db.add(click)
        self.db.flush()
        try:
            result = self.client.create_tracking_link(campaign_id, [product_url], tracking_id)
            data = result.get("data", {})
            links = data.get("success_link", [])
            if not result.get("success") or not links:
                click.status = "ERROR"
            else:
                link = links[0]
                click.aff_link = link.get("aff_link")
                click.short_link = link.get("short_link")
                click.url_origin = link.get("url_origin")
                click.status = "CREATED"
        except Exception:
            click.status = "ERROR"
            raise
        self.db.flush()
        return click

    def upsert_order(self, record: dict[str, Any]) -> AffiliateOrder:
        merchant = str(record.get("merchant") or "unknown")
        external_id = str(record.get("order_id") or record.get("id") or "")
        if not external_id:
            raise ValueError("AccessTrade order is missing order_id")
        order = self.db.query(AffiliateOrder).filter_by(network="ACCESSTRADE", merchant=merchant, external_order_id=external_id).one_or_none()
        tracking_id = _tracking_value(record)
        click = self.db.query(AffiliateClick).filter_by(tracking_id=tracking_id).one_or_none() if tracking_id else None
        if order is None:
            order = AffiliateOrder(network="ACCESSTRADE", merchant=merchant, external_order_id=external_id, raw_data=record, status=int(record.get("status", 0)))
            self.db.add(order)
        order.raw_data = record
        order.status = int(record.get("status", 0))
        order.tracking_id = tracking_id
        order.user_id = click.user_id if click else None
        order.billing = record.get("billing")
        order.commission = record.get("commission")
        order.products_count = record.get("products_count")
        order.at_product_link = record.get("at_product_link")
        if not click and self.db.query(UnmatchedAffiliateOrder).filter_by(
            network="ACCESSTRADE", merchant=merchant, external_order_id=external_id, resolved_at=None
        ).first() is None:
            unmatched = UnmatchedAffiliateOrder(network="ACCESSTRADE", merchant=merchant, external_order_id=external_id, tracking_value=tracking_id, raw_data=record, reason="Tracking identifier was not returned explicitly by AccessTrade")
            self.db.add(unmatched)
        self.db.flush()
        return order

    def upsert_transaction(self, record: dict[str, Any]) -> AffiliateTransaction:
        merchant = str(record.get("merchant") or "unknown")
        transaction_id = str(record.get("transaction_id") or "")
        product_id = str(record.get("product_id") or "")
        if not transaction_id:
            raise ValueError("AccessTrade transaction is missing transaction_id")
        transaction = self.db.query(AffiliateTransaction).filter_by(network="ACCESSTRADE", merchant=merchant, transaction_id=transaction_id, product_id=product_id).one_or_none()
        if transaction is None:
            transaction = AffiliateTransaction(network="ACCESSTRADE", merchant=merchant, transaction_id=transaction_id, product_id=product_id, raw_data=record, status=int(record.get("status", 0)))
            self.db.add(transaction)
        transaction.raw_data = record
        transaction.status = int(record.get("status", 0))
        transaction.is_confirmed = record.get("is_confirmed")
        transaction.tracking_id = _tracking_value(record)
        click = self.db.query(AffiliateClick).filter_by(tracking_id=transaction.tracking_id).one_or_none() if transaction.tracking_id else None
        transaction.user_id = click.user_id if click else None
        transaction.product_name = record.get("product_name")
        transaction.transaction_value = _number(record.get("transaction_value"))
        transaction.commission = _number(record.get("commission"))
        self.db.flush()
        return transaction