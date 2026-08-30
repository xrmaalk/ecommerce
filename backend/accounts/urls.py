from django.urls import path

from .views import (
    CsrfTokenView,
    CurrentCustomerView,
    PasswordChangeView,
    RegisterView,
    SignInView,
    SignOutView,
)

app_name = "accounts"

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("sign-in/", SignInView.as_view(), name="sign-in"),
    path("sign-out/", SignOutView.as_view(), name="sign-out"),
    path("me/", CurrentCustomerView.as_view(), name="me"),
    path("password/", PasswordChangeView.as_view(), name="password"),
]

