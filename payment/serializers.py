# payments/serializers.py
from rest_framework import serializers
from .models import Payment


class CreatePaymentSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(write_only=True)  # Paylink slug

    class Meta:
        model = Payment
        fields = ["slug", "amount"]
