# payments/urls.py
from django.urls import path
from .views import  CreatePaymentAPIView, VerifyPaymentAPIView, VerifyPaymentOTPAPIView

urlpatterns = [
    # API to create reusable paylink

    # API to create payment (pending)
    path("payment/create/", CreatePaymentAPIView.as_view(), name="create-payment"),

    # API to mark payment as success
    path("payment/verify/", VerifyPaymentAPIView.as_view(), name="mark-payment-success"),
    
     # Verify MoMo OTP
    path("payment/verify-otp/", VerifyPaymentOTPAPIView.as_view(), name="verify-payment-otp"),

]
