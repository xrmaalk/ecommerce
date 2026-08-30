import json

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from catalog.models import Product

from .models import CheckoutSession, Order, PaymentWebhookEvent, ShippingRate
from .paypal import PayPalClient, PayPalError
from .serializers import (
    CartItemWriteSerializer,
    CartMergeSerializer,
    CartSerializer,
    CheckoutCreateOrderSerializer,
    CheckoutSessionSerializer,
    OrderSerializer,
    ShippingAddressSerializer,
    ShippingRateSerializer,
)
from .services import (
    CommerceError,
    capture_checkout,
    cart_queryset,
    complete_checkout,
    create_checkout_session,
    create_paypal_order,
    get_active_cart,
    merge_cart,
    set_cart_item,
)
from .tax import TaxUnavailable


def commerce_error_response(error):
    code = status.HTTP_503_SERVICE_UNAVAILABLE if isinstance(error, (TaxUnavailable, PayPalError)) else status.HTTP_400_BAD_REQUEST
    return Response({"detail": str(error)}, status=code)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = cart_queryset().get(pk=get_active_cart(request.user).pk)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = CartItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cart = set_cart_item(
                request.user,
                serializer.validated_data["product"],
                serializer.validated_data["quantity"],
            )
        except CommerceError as error:
            return commerce_error_response(error)
        return Response(CartSerializer(cart, context={"request": request}).data)


class CartMergeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = merge_cart(request.user, serializer.validated_data["items"])
        return Response(CartSerializer(cart, context={"request": request}).data)


class ShippingRateListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShippingRateSerializer
    pagination_class = None
    queryset = ShippingRate.objects.filter(is_active=True)


class CheckoutConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "paypal_client_id": settings.PAYPAL_CLIENT_ID,
            "paypal_mode": settings.PAYPAL_MODE,
            "currency": "CAD",
            "paypal_enabled": bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET),
        })


class CheckoutQuoteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "checkout"

    def post(self, request):
        serializer = ShippingAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            checkout = create_checkout_session(request.user, serializer.validated_data)
        except (CommerceError, TaxUnavailable) as error:
            return commerce_error_response(error)
        return Response(CheckoutSessionSerializer(checkout).data, status=status.HTTP_201_CREATED)


class PayPalOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request):
        serializer = CheckoutCreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        checkout = serializer.validated_data["checkout_session"]
        try:
            paypal_order_id = create_paypal_order(checkout)
        except (CommerceError, PayPalError) as error:
            return commerce_error_response(error)
        return Response({"paypal_order_id": paypal_order_id})


class PayPalOrderCaptureView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request):
        serializer = CheckoutCreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        checkout = serializer.validated_data["checkout_session"]
        try:
            order = capture_checkout(checkout)
        except (CommerceError, PayPalError) as error:
            return commerce_error_response(error)
        return Response(OrderSerializer(order).data)


class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    lookup_field = "number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


def paypal_header_map(request):
    return {
        "PAYPAL-AUTH-ALGO": request.headers.get("PayPal-Auth-Algo", ""),
        "PAYPAL-CERT-URL": request.headers.get("PayPal-Cert-Url", ""),
        "PAYPAL-TRANSMISSION-ID": request.headers.get("PayPal-Transmission-Id", ""),
        "PAYPAL-TRANSMISSION-SIG": request.headers.get("PayPal-Transmission-Sig", ""),
        "PAYPAL-TRANSMISSION-TIME": request.headers.get("PayPal-Transmission-Time", ""),
    }


@csrf_exempt
@require_POST
def paypal_webhook(request):
    try:
        event = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    event_id = event.get("id")
    event_type = event.get("event_type", "")
    if not event_id or not event_type:
        return JsonResponse({"detail": "Missing PayPal event identity."}, status=400)

    webhook, created = PaymentWebhookEvent.objects.get_or_create(
        external_id=event_id,
        defaults={"event_type": event_type, "payload": event},
    )
    if not created and webhook.status in (
        PaymentWebhookEvent.Status.PROCESSED,
        PaymentWebhookEvent.Status.IGNORED,
    ):
        return JsonResponse({"status": webhook.status})
    if not created:
        webhook.event_type = event_type
        webhook.payload = event
        webhook.processing_error = ""
        webhook.save(update_fields=("event_type", "payload", "processing_error"))

    try:
        if not PayPalClient().verify_webhook(paypal_header_map(request), event):
            webhook.status = PaymentWebhookEvent.Status.FAILED
            webhook.processing_error = "PayPal signature verification failed."
            webhook.save(update_fields=("status", "processing_error"))
            return JsonResponse({"detail": "Signature verification failed."}, status=400)
        webhook.status = PaymentWebhookEvent.Status.VERIFIED
        webhook.save(update_fields=("status",))

        if event_type != "PAYMENT.CAPTURE.COMPLETED":
            webhook.status = PaymentWebhookEvent.Status.IGNORED
        else:
            resource = event.get("resource", {})
            paypal_order_id = (
                resource.get("supplementary_data", {})
                .get("related_ids", {})
                .get("order_id")
            )
            checkout = CheckoutSession.objects.filter(paypal_order_id=paypal_order_id).first()
            if not checkout:
                webhook.status = PaymentWebhookEvent.Status.IGNORED
            else:
                amount = resource.get("amount", {})
                complete_checkout(
                    checkout.id,
                    capture_id=resource.get("id", ""),
                    amount_value=amount.get("value", "0"),
                    currency_code=amount.get("currency_code", ""),
                )
                webhook.status = PaymentWebhookEvent.Status.PROCESSED
        webhook.processed_at = timezone.now()
        webhook.save(update_fields=("status", "processed_at"))
        return JsonResponse({"status": webhook.status})
    except Exception as error:
        webhook.status = PaymentWebhookEvent.Status.FAILED
        webhook.processing_error = str(error)[:2000]
        webhook.save(update_fields=("status", "processing_error"))
        return JsonResponse({"detail": "Webhook processing failed."}, status=500)
