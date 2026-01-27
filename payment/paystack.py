import requests
import hmac
import hashlib
import json
from django.conf import settings
from decimal import Decimal


class PaystackMobileMoney:
    BASE_URL = "https://api.paystack.co"

    # -----------------------------
    # Mobile Money Providers
    # -----------------------------
    PROVIDERS = {
        "MTN": {"code": "mtn", "countries": ["Ghana", "CIV"]},
        "ATMoney_Airtel": {"code": "atl", "countries": ["Ghana", "Kenya"]},
        "Telecel": {"code": "vod", "countries": ["Ghana"]},
        "M-PESA": {"code": "mpesa", "countries": ["Kenya"]},
        "MPESA_Offline": {"code": "mpesa_offline", "countries": ["Kenya"]},
        "M-PESA_Till": {"code": "mptill", "countries": ["Kenya"]},
        "Orange": {"code": "orange", "countries": ["CIV"]},
        "Wave": {"code": "wave", "countries": ["CIV"]},
    }
    
    PESSEWA_MULTIPLIER = 100

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    # -----------------------------
    # List Providers
    # -----------------------------
    @classmethod
    def list_providers(cls):
        return list(cls.PROVIDERS.keys())

    # -----------------------------
    # Get Provider Code
    # -----------------------------
    @classmethod
    def get_provider_code(cls, provider_name: str):
        return cls.PROVIDERS.get(provider_name, {}).get("code")

    # -----------------------------
    # Check if Provider Exists
    # -----------------------------
    @classmethod
    def is_valid_provider(cls, provider_name: str):
        return provider_name in cls.PROVIDERS

    # ------------------------------------
    # CREATE MOBILE MONEY CHARGE
    # ------------------------------------
    def charge(
        self,
        email: str,
        amount: int,
        currency: str,
        provider_name: str,
        phone: str = None,
        account: str = None,
        reference: str = None,
        metadata: dict = None,
    ):
        """
        amount: in subunit (GHS pesewas / KES cents)
        provider_name: human-friendly name, e.g., 'MTN', 'M-PESA'
        """

        if not self.is_valid_provider(provider_name):
            raise ValueError(f"Invalid provider: {provider_name}. Use PaystackMobileMoney.list_providers()")

        provider_code = self.get_provider_code(provider_name)

        mobile_money = {"provider": provider_code}
        if phone:
            mobile_money["phone"] = phone
        if account:
            mobile_money["account"] = account

        payload = {
            "email": email,
            "amount": self.to_pesewas(amount),
            "currency": currency,
            "mobile_money": mobile_money,
        }

        if reference:
            payload["reference"] = reference
        if metadata:
            payload["metadata"] = metadata

        response = requests.post(
            f"{self.BASE_URL}/charge",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        return response.json()
    
    def submit_otp(self, otp, reference):
        url = f"{self.BASE_URL}/charge/submit_otp"

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "otp": otp,
            "reference": reference,
        }

        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    @staticmethod
    def to_pesewas(amount):
        """
        Convert GHS amount to pesewas (Paystack expects subunit).
        Accepts int, float, or Decimal.
        """
        if isinstance(amount, Decimal):
            return int(amount * PaystackMobileMoney.PESSEWA_MULTIPLIER)

        return int(Decimal(str(amount)) * PaystackMobileMoney.PESSEWA_MULTIPLIER)

    # ------------------------------------
    # VERIFY TRANSACTION (FALLBACK)
    # ------------------------------------
    def verify(self, reference: str):
        response = requests.get(
            f"{self.BASE_URL}/transaction/verify/{reference}",
            headers=self.headers,
            timeout=30,
        )
        return response.json()

