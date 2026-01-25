from rest_framework import serializers
from .models import PaymentChannel
from django.db.models import Sum
from decimal import Decimal


class PaymentChannelSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and listing PaymentChannels (Paylink & USSD).
    """
    class Meta:
        model = PaymentChannel
        fields = [
            "id",
            "name",
            "slug",
            "amount",
            "currency",
            "paylink_enabled",
            "paylink",
            "ussd_enabled",
            "ussd",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at", "paylink", "ussd"]




class PaymentChannelUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a PaymentChannel.
    Only specific fields can be updated.
    """

    # Optional validation for amount
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.01")
    )

    class Meta:
        model = PaymentChannel
        fields = [
            "name",
            "amount",
            "currency",
            "paylink_enabled",
            "ussd_enabled"
        ]
        extra_kwargs = {
            "name": {"required": False},
            "currency": {"required": False},
            "paylink_enabled": {"required": False},
            "ussd_enabled": {"required": False},
        }

    def validate_name(self, value):
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip() if value else value



class PaymentChannelStatsSerializer(serializers.Serializer):
    total_channels = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_created_slug = serializers.CharField(allow_null=True)
    last_created_at = serializers.DateTimeField(allow_null=True)

    # New fields
    payments_count = serializers.SerializerMethodField()
    paylink_amount = serializers.SerializerMethodField()
    ussd_amount = serializers.SerializerMethodField()

    def get_payments_count(self, obj):
        # Count of all payments for this channel
        return obj.payments.count()

    def get_paylink_amount(self, obj):
        # Sum of all payments made via Paylink
        return obj.payments.filter(method="paylink", status="success").aggregate(total=Sum("amount"))["total"] or 0

    def get_ussd_amount(self, obj):
        # Sum of all payments made via USSD
        return obj.payments.filter(method="ussd", status="success").aggregate(total=Sum("amount"))["total"] or 0
