from rest_framework import serializers
from .models import Payment


class CreatePaymentSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(write_only=True)

    charge_type = serializers.ChoiceField(
        choices=[("momo", "Mobile Money"), ("card", "Card")],
        write_only=True
    )

    phone_number = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    # Optional email
    email = serializers.EmailField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Payment
        fields = ["slug", "amount", "charge_type", "phone_number", "email"]

    def validate(self, attrs):
        charge_type = attrs.get("charge_type")
        phone_number = attrs.get("phone_number", "").strip()

        # MoMo requires phone number
        if charge_type == "momo" and not phone_number:
            raise serializers.ValidationError({
                "phone_number": "Phone number is required for mobile money (MoMo) payments."
            })

        # Validate phone number format for MoMo
        if charge_type == "momo":
            if not phone_number.isdigit():
                raise serializers.ValidationError({
                    "phone_number": "Phone number must contain only digits."
                })

            # Optional but recommended: Ghana phone length
            if len(phone_number) not in (9, 10, 12):
                raise serializers.ValidationError({
                    "phone_number": "Invalid phone number length."
                })

        return attrs
    
    
    
class VerifyPaymentOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(
        max_length=10,
        help_text="One-time password sent to the customer"
    )
    reference = serializers.CharField(
        help_text="Payment reference returned during charge initialization"
    )