from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from catalog.models import Category, Product
from .models import Cart


@override_settings(
    ALLOWED_HOSTS=["api.organicemperor.com"],
    CSRF_TRUSTED_ORIGINS=["https://organicemperor.com", "https://www.organicemperor.com"],
    CORS_ALLOWED_ORIGINS=["https://organicemperor.com", "https://www.organicemperor.com"],
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class StorefrontCartCsrfTests(APITestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        user = get_user_model().objects.create_user(username="csrf-shopper")
        self.client.force_login(user)
        category = Category.objects.create(name="Care", slug="csrf-care")
        self.product = Product.objects.create(
            name="Soap", slug="csrf-soap", sku="csrf-soap", category=category,
            price_cad="10.00", inventory_quantity=5,
        )
        response = self.client.get(reverse("accounts:csrf"), secure=True, HTTP_HOST="api.organicemperor.com")
        self.token = response.data["csrf_token"]
        self.assertTrue(response.cookies["csrftoken"]["secure"])

    def update_cart(self, origin, token=None):
        headers = {"HTTP_HOST": "api.organicemperor.com", "HTTP_ORIGIN": origin}
        if token is not None:
            headers["HTTP_X_CSRFTOKEN"] = token
        return self.client.put(
            reverse("commerce:cart-item"), {"product_id": self.product.pk, "quantity": 1},
            format="json", secure=True, **headers,
        )

    def test_exact_https_storefront_origins_allow_authenticated_cart_updates(self):
        for origin in ("https://organicemperor.com", "https://www.organicemperor.com"):
            with self.subTest(origin=origin):
                response = self.update_cart(origin, self.token)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["items"][0]["quantity"], 1)
                self.assertEqual(response["Access-Control-Allow-Origin"], origin)

    @override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:5173"])
    def test_development_only_origin_override_reproduces_the_live_error(self):
        response = self.update_cart("https://organicemperor.com", self.token)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Origin checking failed", response.data["detail"])
        self.assertIn("https://organicemperor.com does not match any trusted origins", response.data["detail"])
        # CORS already permits the storefront; it does not replace CSRF trust.
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://organicemperor.com")
        self.assertFalse(Cart.objects.exists())

    def test_untrusted_origins_do_not_change_the_cart(self):
        for origin in (
            "https://evil.example", "https://organicemperor.com.evil.example",
            "http://organicemperor.com", "https://organicemperor.com:8443",
        ):
            with self.subTest(origin=origin):
                response = self.update_cart(origin, self.token)
                self.assertEqual(response.status_code, 403)
                self.assertIn("Origin checking failed", response.data["detail"])
                self.assertNotIn("Access-Control-Allow-Origin", response)
                self.assertFalse(Cart.objects.exists())

    def test_trusted_origin_still_requires_a_valid_csrf_token(self):
        for token in (None, "A" * 64):
            with self.subTest(token_supplied=token is not None):
                response = self.update_cart("https://organicemperor.com", token)
                self.assertEqual(response.status_code, 403)
                self.assertIn("CSRF", response.data["detail"])
                self.assertFalse(Cart.objects.exists())

    def test_csrf_token_does_not_replace_customer_authentication(self):
        self.client.logout()
        response = self.update_cart("https://organicemperor.com", self.token)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Cart.objects.exists())
