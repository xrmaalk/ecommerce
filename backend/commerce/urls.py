from django.urls import path

from .views import (
    CartItemView,
    CartMergeView,
    CartView,
    CheckoutConfigView,
    CheckoutQuoteView,
    OrderDetailView,
    OrderListView,
    PayPalOrderCaptureView,
    PayPalOrderCreateView,
    ShippingRateListView,
    paypal_webhook,
)

app_name = "commerce"

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemView.as_view(), name="cart-item"),
    path("cart/merge/", CartMergeView.as_view(), name="cart-merge"),
    path("shipping-rates/", ShippingRateListView.as_view(), name="shipping-rates"),
    path("checkout/config/", CheckoutConfigView.as_view(), name="checkout-config"),
    path("checkout/quote/", CheckoutQuoteView.as_view(), name="checkout-quote"),
    path("checkout/paypal/create/", PayPalOrderCreateView.as_view(), name="paypal-create"),
    path("checkout/paypal/capture/", PayPalOrderCaptureView.as_view(), name="paypal-capture"),
    path("orders/", OrderListView.as_view(), name="orders"),
    path("orders/<str:number>/", OrderDetailView.as_view(), name="order-detail"),
    path("webhooks/paypal/", paypal_webhook, name="paypal-webhook"),
]

