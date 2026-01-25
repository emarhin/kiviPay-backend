# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from datetime import datetime
# from .models import  Payment
# from payment.serializers import CreatePaymentSerializer
# from paylink.models import PaymentChannel


# # 2️⃣ Create a payment (pending)
# class CreatePaymentAPIView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = CreatePaymentSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)

#         slug = serializer.validated_data["slug"]
#         amount = serializer.validated_data["amount"]

#         try:
#             paylink = PaymentChannel.objects.get(slug=slug)
#         except PaymentChannel.DoesNotExist:
#             return Response({"error": "Paylink not found"}, status=404)

#         # Payment reference can also use datetime to ensure uniqueness
#         reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

#         payment = Payment.objects.create(
#             paylink=paylink,
#             amount=amount,
#             reference=reference,
#             status="pending"
#         )

#         return Response({
#             "message": "Payment created",
#             "payment_reference": reference,
#             "status": payment.status
#         })


# # 3️⃣ Simulate marking payment as success (admin can call)
# class MarkPaymentSuccessAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         reference = request.data.get("reference")
#         try:
#             payment = Payment.objects.get(reference=reference)
#             payment.status = "success"
#             payment.save()
#             return Response({"message": "Payment marked as success"})
#         except Payment.DoesNotExist:
#             return Response({"error": "Payment not found"}, status=404)