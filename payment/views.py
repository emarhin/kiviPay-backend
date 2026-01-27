from datetime import datetime
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import Payment
from .serializers import CreatePaymentSerializer, VerifyPaymentOTPSerializer
from paychannel.models import PaymentChannel
from .paystack import PaystackMobileMoney
from config.settings import PAYSTACK_SECRET_KEY


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
                "slug": "string-20260125140829334466",
                "amount": 100.00,
                "charge_type": "momo",
                "phone_number": "0551234987",
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
        charge_type = serializer.validated_data["charge_type"]
        phone_number = serializer.validated_data["phone_number"]
        email = request.data.get("email")
        

        try:
            payment_channel = PaymentChannel.objects.get(slug=slug)
        except PaymentChannel.DoesNotExist:
            return Response(
                {"error": "pay channel not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # print("secret key paystack", PAYSTACK_SECRET_KEY)
        
        match charge_type:
            case "momo":
                if not phone_number:
                    return Response({"error": "Phone number is required for MoMo payments"},status=400)
                    
                #if no email generate email
                if not email:
                    email =  f"{phone_number}@gmail.com"
            
                paymentInitiziation = PaystackMobileMoney(PAYSTACK_SECRET_KEY)
                momo_charge = paymentInitiziation.charge(email, int(amount), "GHS", "MTN", phone_number, "", reference, {"key": "value"})
                print(momo_charge)
            
            case "card":
                return Response({"error": "Card payments are not supported yet"},status=400)
        

        
        if momo_charge.get("status") is True:
            payment = Payment.objects.create(
                channel=payment_channel,
                amount=amount,
                reference=reference,
                email = email,
                phone_number = phone_number,
                status="pending",
            )
                 
            return Response(
                {
                    "message": momo_charge.get("message"),
                    "payment_reference": reference,
                    "status": momo_charge.get("data").get("status"),
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






@extend_schema(
    summary="Verify MoMo OTP",
    description=(
        "Verify the OTP sent to the customer after initiating a mobile money charge.\n\n"
        "⚠️ This endpoint only verifies the OTP. "
        "It does NOT confirm that the payment was successful.\n\n"
        "Final payment confirmation must be done via Paystack webhook "
        "or transaction verification."
    ),
    request=VerifyPaymentOTPSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "otp_verified": {"type": "boolean"},
                "payment_status": {"type": "string"},
            },
        },
        400: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "otp_verified": {"type": "boolean"},
            },
        },
        404: {"description": "Pending payment not found"},
    },
    tags=["Payments"],
)
class VerifyPaymentOTPAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyPaymentOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data["otp"]
        reference = serializer.validated_data["reference"]

        if not otp or not reference:
            return Response(
                {"error": "OTP and reference are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Payment.objects.get(
                reference=reference,
                status="pending",
            )
        except Payment.DoesNotExist:
            return Response(
                {"message": "Pending payment not found","otp_verified": False},
                status=status.HTTP_404_NOT_FOUND,
            )

        paystack = PaystackMobileMoney(PAYSTACK_SECRET_KEY)
        result = paystack.submit_otp(otp, reference)
        
        print(result)

        # ❌ Invalid reference or OTP
        if result.get("status") is False:
            return Response(
                {
                    "message": result.get("message", "OTP verification failed"),
                    "otp_verified": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_status = result.get("data", {}).get("status")
        
        match  otp_status:
            case "pending" | "success":
                return Response(
                {
                    "message": result.get("data", {}).get("message"),
                    "otp_verified": True,
                    "raw": result,
                },
                status=status.HTTP_200_OK,
            )
            case "failed":
                return Response(
                {
                    "message": result.get("data", {}).get("message"),
                    "otp_verified": False,
                    "raw": result,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
            case "requery":
                return Response(
                {
                    "message": result.get("data", {}).get( "message"),
                    "otp_verified": True,
                    "raw": result,
                },
                status=status.HTTP_200_OK,
            )
            case _:
                return Response(
                {
                    "message": "OTP verification failed",
                    "otp_verified": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
                
        return Response(
            {
                "message": "Unable to verify OTP",
                "otp_verified": False,
                "raw": result,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
