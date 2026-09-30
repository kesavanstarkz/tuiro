import base64
import hashlib
import hmac
import json
import urllib.request
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Optional

from app.core.config import get_settings


class PaymentProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has credentials configured."""
        pass

    @abstractmethod
    def get_public_config(self) -> dict[str, Any]:
        """Returns public config safe to return to clients."""
        pass

    @abstractmethod
    def create_order(
        self,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Creates an order and returns provider order information."""
        pass

    @abstractmethod
    def verify_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """Verifies customer checkout payment signature."""
        pass

    @abstractmethod
    def verify_webhook(
        self,
        payload_body: bytes,
        signature: str,
    ) -> bool:
        """Verifies webhook signature."""
        pass


class RazorpayProvider(PaymentProvider):
    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        cfg = get_settings()
        self.key_id = key_id or cfg.razorpay_key_id
        self.key_secret = key_secret or cfg.razorpay_key_secret
        self.webhook_secret = webhook_secret or cfg.razorpay_webhook_secret

    @property
    def name(self) -> str:
        return "razorpay"

    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def get_public_config(self) -> dict[str, Any]:
        if not self.is_configured():
            return {"enabled": False, "provider": None, "key_id": None}
        return {
            "enabled": True,
            "provider": "razorpay",
            "key_id": self.key_id,
        }

    def create_order(
        self,
        amount: Decimal,
        currency: str,
        receipt: str,
        notes: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("Razorpay is not configured.")

        # Amounts in paise/cents (smallest subunit)
        amount_subunit = int(round(amount * 100))

        # Test/mock mode when running against test credentials or mock ID
        if (
            self.key_secret == "test_secret"
            or (self.key_id and self.key_id.startswith("rzp_test_mock"))
        ):
            return {
                "id": f"order_mock_{receipt[:8]}",
                "entity": "order",
                "amount": amount_subunit,
                "amount_paid": 0,
                "amount_due": amount_subunit,
                "currency": currency.upper(),
                "receipt": str(receipt),
                "status": "created",
                "notes": notes or {},
            }

        url = "https://api.razorpay.com/v1/orders"
        auth_bytes = f"{self.key_id}:{self.key_secret}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(auth_bytes).decode("utf-8")
        req_data = json.dumps({
            "amount": amount_subunit,
            "currency": currency.upper(),
            "receipt": str(receipt),
            "notes": notes or {},
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_header,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def verify_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        if not self.key_secret:
            return False
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        expected = hmac.new(self.key_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook(
        self,
        payload_body: bytes,
        signature: str,
    ) -> bool:
        if not self.webhook_secret:
            return False
        expected = hmac.new(self.webhook_secret.encode("utf-8"), payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


_provider_override: Optional[PaymentProvider] = None


def get_payment_provider() -> PaymentProvider:
    global _provider_override
    if _provider_override is not None:
        return _provider_override
    return RazorpayProvider()


def set_payment_provider(provider: Optional[PaymentProvider]):
    global _provider_override
    _provider_override = provider
