import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class PayPalError(Exception):
    pass


class PayPalConfigurationError(PayPalError):
    pass


class PayPalClient:
    timeout = 20

    def __init__(self):
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.webhook_id = settings.PAYPAL_WEBHOOK_ID
        self.base_url = (
            "https://api-m.paypal.com"
            if settings.PAYPAL_MODE == "live"
            else "https://api-m.sandbox.paypal.com"
        )

    def _require_credentials(self):
        if not self.client_id or not self.client_secret:
            raise PayPalConfigurationError("PayPal credentials are not configured.")

    def _request(self, method, path, *, payload=None, headers=None, basic_auth=False):
        self._require_credentials()
        request_headers = {"Accept": "application/json", **(headers or {})}
        if basic_auth:
            encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            request_headers["Authorization"] = f"Basic {encoded}"
        data = None
        if payload is not None:
            if isinstance(payload, dict):
                data = json.dumps(payload).encode()
                request_headers["Content-Type"] = "application/json"
            else:
                data = payload.encode()
        request = Request(f"{self.base_url}{path}", data=data, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode()
                return json.loads(body) if body else {}
        except HTTPError as error:
            error.read()
            raise PayPalError(f"PayPal rejected the checkout request (HTTP {error.code}).") from error
        except (URLError, TimeoutError) as error:
            raise PayPalError("PayPal could not be reached. Please try again.") from error

    def access_token(self):
        response = self._request(
            "POST",
            "/v1/oauth2/token",
            payload="grant_type=client_credentials",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            basic_auth=True,
        )
        token = response.get("access_token")
        if not token:
            raise PayPalError("PayPal did not return an access token.")
        return token

    def authenticated_request(self, method, path, *, payload=None, request_id=None):
        headers = {"Authorization": f"Bearer {self.access_token()}"}
        if request_id:
            headers["PayPal-Request-Id"] = str(request_id)
        return self._request(method, path, payload=payload, headers=headers)

    def create_order(self, payload, request_id):
        return self.authenticated_request(
            "POST", "/v2/checkout/orders", payload=payload, request_id=request_id
        )

    def capture_order(self, paypal_order_id, request_id):
        return self.authenticated_request(
            "POST",
            f"/v2/checkout/orders/{paypal_order_id}/capture",
            payload={},
            request_id=request_id,
        )

    def verify_webhook(self, headers, event):
        if not self.webhook_id:
            raise PayPalConfigurationError("PAYPAL_WEBHOOK_ID is not configured.")
        payload = {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
            "cert_url": headers.get("PAYPAL-CERT-URL", ""),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
            "webhook_id": self.webhook_id,
            "webhook_event": event,
        }
        response = self.authenticated_request(
            "POST", "/v1/notifications/verify-webhook-signature", payload=payload
        )
        return response.get("verification_status") == "SUCCESS"
