from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import Payment
from .serializers import CreatePaymentSerializer
from paychannel.models import PaymentChannel


# ================================
# 2️⃣ Create a payment (pending)
# ================================

@extend_schema(
    summary="Create payment",
    description=(
        "Create a new payment for a paylink. "
        "The payment is created with **pending** status and a unique reference."
    ),
    request=CreatePaymentSerializer,
    responses={
        201: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "payment_reference": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        404: {"description": "Paylink not found"},
    },
    examples=[
        OpenApiExample(
            name="Create payment example",
            value={
                "slug": "my-paylink-123",
                "amount": 100.00
            },
            request_only=True,
        )
    ],
    tags=["Payments"],
)
class CreatePaymentAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        slug = serializer.validated_data["slug"]
        amount = serializer.validated_data["amount"]

        try:
            paylink = PaymentChannel.objects.get(slug=slug)
        except PaymentChannel.DoesNotExist:
            return Response(
                {"error": "Paylink not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        payment = Payment.objects.create(
            paylink=paylink,
            amount=amount,
            reference=reference,
            status="pending",
        )

        return Response(
            {
                "message": "Payment created",
                "payment_reference": reference,
                "status": payment.status,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================
# 3️⃣ Mark payment as success (admin)
# =========================================

@extend_schema(
    summary="Mark payment as successful",
    description=(
        "Manually mark a payment as **success** using its reference. "
        "This endpoint is typically used by admins or webhook simulations."
    ),
    request={
        "type": "object",
        "properties": {
            "reference": {
                "type": "string",
                "example": "PAY-20260125153000123456",
            }
        },
        "required": ["reference"],
    },
    responses={
        200: {"description": "Payment marked as success"},
        404: {"description": "Payment not found"},
    },
    tags=["Payments"],
)
class MarkPaymentSuccessAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")

        try:
            payment = Payment.objects.get(reference=reference)
            payment.status = "success"
            payment.save()

            return Response(
                {"message": "Payment marked as success"},
                status=status.HTTP_200_OK,
            )

        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
