from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication"
        ],
        "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
        "DEFAULT_THROTTLE_RATES": {"authentication": "1000/minute"},
    },
)
class AccountAuthenticationTests(APITestCase):
    password = "Cedar&Comfrey2026!"

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        response = self.client.get(reverse("accounts:csrf"))
        self.csrf_token = response.data["csrf_token"]

    @property
    def csrf(self):
        return {"HTTP_X_CSRFTOKEN": self.csrf_token}

    def create_user(self, email="customer@example.com"):
        return User.objects.create_user(
            username=email,
            email=email,
            first_name="Maya",
            last_name="Green",
            password=self.password,
        )

    def test_registration_requires_csrf(self):
        response = self.client.post(reverse("accounts:register"), {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_registration_creates_user_and_authenticated_session(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "NEW@Example.com",
                "first_name": "Avery",
                "last_name": "Stone",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
            **self.csrf,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "new@example.com")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.get(email="new@example.com").check_password(self.password))
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, status.HTTP_200_OK)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        self.create_user()
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "CUSTOMER@example.com",
                "first_name": "Other",
                "last_name": "Customer",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
            **self.csrf,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_sign_in_and_sign_out(self):
        self.create_user()
        sign_in = self.client.post(
            reverse("accounts:sign-in"),
            {"email": "CUSTOMER@EXAMPLE.COM", "password": self.password},
            format="json",
            **self.csrf,
        )
        self.assertEqual(sign_in.status_code, status.HTTP_200_OK)
        self.assertEqual(sign_in.data["first_name"], "Maya")

        # Django rotates the CSRF secret at sign-in; mirror the frontend refresh.
        self.csrf_token = self.client.get(reverse("accounts:csrf")).data["csrf_token"]
        sign_out = self.client.post(reverse("accounts:sign-out"), **self.csrf)
        self.assertEqual(sign_out.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.client.get(reverse("accounts:me")).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_sign_in_uses_generic_error_for_bad_credentials(self):
        self.create_user()
        response = self.client.post(
            reverse("accounts:sign-in"),
            {"email": "customer@example.com", "password": "WrongPassword!234"},
            format="json",
            **self.csrf,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "The email or password is incorrect.")

    def test_current_customer_requires_authentication(self):
        response = self.client.get(reverse("accounts:me"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_can_be_updated(self):
        self.client.force_login(self.create_user())
        response = self.client.patch(
            reverse("accounts:me"),
            {"first_name": "Amara", "email": "amara@example.com"},
            format="json",
            **self.csrf,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Amara")
        self.assertEqual(response.data["email"], "amara@example.com")
        user = User.objects.get(pk=response.data["id"])
        self.assertEqual(user.username, "amara@example.com")

    def test_password_change_keeps_session_authenticated(self):
        self.client.force_login(self.create_user())
        new_password = "Lavender&Gold2027!"
        response = self.client.post(
            reverse("accounts:password"),
            {
                "current_password": self.password,
                "new_password": new_password,
                "new_password_confirm": new_password,
            },
            format="json",
            **self.csrf,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("accounts:me")).status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.get(email="customer@example.com").check_password(new_password))
