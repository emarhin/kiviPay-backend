# authentications/serializers.py
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer
from .models import CustomUser


from rest_framework import serializers
from .models import CustomUser
import uuid, re

class CustomRegisterSerializer(RegisterSerializer):
    username = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    phone_number = serializers.CharField(required=True, max_length=15)
    email = serializers.EmailField(required=True)

    def validate_email(self, email):
        if CustomUser.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return email

    def generate_username(self, email):
        """
        Auto-generate unique username
        example: emmanuel_8f32a1
        """
        base = re.sub(r'[^a-zA-Z0-9]', '', email.split('@')[0]).lower()
        unique = uuid.uuid4().hex[:6]
        return f"{base}_{unique}"

    def get_cleaned_data(self):
        email = self.validated_data.get('email')
        username = self.generate_username(email)

        return {
            'username': username,  # ✅ auto-created
            'email': email,
            'password': self.validated_data.get('password1'),
            'phone_number': self.validated_data.get('phone_number'),
            'first_name': self.validated_data.get('first_name'),
            'last_name': self.validated_data.get('last_name'),
        }
class CustomUserDetailsSerializer(UserDetailsSerializer):
    """
    Controls what /api/auth/user/ returns
    """
    class Meta(UserDetailsSerializer.Meta):
        model = CustomUser
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
            'groups',
            'user_permissions',
            'phone_number',
            'phone_verified',
            'username',
        )
    def validate_username(self, username):
        # completely disable username validation
        return None
