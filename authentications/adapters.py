from allauth.account.adapter import DefaultAccountAdapter
from typing import Tuple, Optional
from .models import CustomUser  # or your user model

class MyAccountAdapter(DefaultAccountAdapter):

    # --------------------------
    # Phone number retrieval
    # --------------------------
    def get_phone(self, user) -> Optional[Tuple[str, bool]]:
        """
        Return the phone number and verification status for a given user.
        """
        if hasattr(user, 'phone_number') and user.phone_number:
            return (user.phone_number, user.phone_verified)
        return None

    def set_phone(self, user, phone: str, verified: bool = False):
        """
        Set the phone number for the user, and mark verified if True.
        """
        user.phone_number = phone
        user.phone_verified = verified
        user.save(update_fields=['phone_number', 'phone_verified'])

    def set_phone_verified(self, user, phone: str):
        """
        Mark a phone number as verified.
        """
        if user.phone_number == phone:
            user.phone_verified = True
            user.save(update_fields=['phone_verified'])

    def get_user_by_phone(self, phone: str):
        """
        Lookup a user by phone number.
        """
        try:
            return CustomUser.objects.get(phone_number=phone)
        except CustomUser.DoesNotExist:
            return None

    # --------------------------
    # SMS sending (implement your provider here)
    # --------------------------
    def send_verification_code_sms(self, user, phone: str, code: str, **kwargs):
        """
        Send an SMS with a verification code.
        Use your preferred SMS provider here.
        """
        # Example: print for testing
        print(f"Send SMS to {phone}: Your verification code is {code}")

    def send_unknown_account_sms(self, phone: str, **kwargs):
        """
        Optional: Send SMS if phone not found (enumeration prevention)
        """
        print(f"No account associated with {phone}")
