import uuid
import requests
from decimal import Decimal, ROUND_DOWN
from requests.auth import HTTPBasicAuth
from django.conf import settings


class PaySwitchMobileMoney:
    """
    PaySwitch Mobile Money Integration (GHS only)
    """

    BASE_URL = "https://prod.theteller.net/v1.1"
    PROCESSING_CODE = "000200"

    # -----------------------------
    # Providers
    # -----------------------------
    PROVIDERS = {
        "MTN": {"code": "MTN", "countries": ["Ghana", "CIV"]},
        "ATMoney_Airtel": {"code": "ATL", "countries": ["Ghana", "Kenya"]},
        "Telecel": {"code": "VDF", "countries": ["Ghana"]},
    }

    def __init__(self):
        self.username = settings.PAYSWITCH_USERNAME
        self.api_key = settings.PAYSWITCH_API_KEY
        self.merchant_id = settings.PAYSWITCH_MERCHANT_ID

        self.auth = HTTPBasicAuth(self.username, self.api_key)
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

    # ======================================================
    # MONEY — EXACT RUST EQUIVALENT
    # ======================================================

    def to_minor_units(self, amount: Decimal) -> str:
        """
        Rust equivalent:

        fn to_minor_units(amount: Decimal) -> Result<String, &'static str> {
            if amount.scale() > 2 {
                return Err("Amount has more than 2 decimal places");
            }

            let pesewas = amount
                .checked_mul(Decimal::from(100))
                .and_then(|v| v.to_u64())
                .ok_or("Invalid amount")?;

            Ok(format!("{:012}", pesewas))
        }
        """

        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        # scale() > 2
        if amount.as_tuple().exponent < -2:
            raise ValueError("Amount has more than 2 decimal places")

        pesewas = (amount * Decimal("100")).quantize(
            Decimal("1"),
            rounding=ROUND_DOWN,
        )

        if pesewas < 0:
            raise ValueError("Invalid amount")

        return f"{int(pesewas):012d}"

    # ======================================================
    # HELPERS
    # ======================================================

    def get_provider_code(self, provider_name: str) -> str:
        provider = self.PROVIDERS.get(provider_name)
        if not provider:
            raise ValueError(f"Invalid provider: {provider_name}")
        return provider["code"]

    # ======================================================
    # CHARGE (MoMo ONLY)
    # ======================================================

    def charge(
        self,
        email: str,
        amount,
        currency: str,
        provider_name: str,
        phone: str = None,
        account: str = None,
        reference: str = None,
        metadata: dict = None,
    ):
        """
        amount: GHS (Decimal / int / string)
        currency: GHS only
        """

        if currency.upper() != "GHS":
            raise ValueError("PaySwitch supports GHS only")

        if provider_name not in self.PROVIDERS:
            raise ValueError(f"Invalid provider: {provider_name}")

        subscriber_number = phone or account
        if not subscriber_number:
            raise ValueError("Phone or account number is required")

        payment_reference = reference or f"PAY-{uuid.uuid4().hex[:16]}"

        formatted_amount = self.to_minor_units(Decimal(str(amount)))

        body = {
            "amount": formatted_amount,  # ✅ 12-digit pesewas
            "processing_code": self.PROCESSING_CODE,
            "transaction_id": payment_reference,
            "desc": (
                metadata.get("description")
                if metadata and "description" in metadata
                else "Mobile Money Payment"
            ),
            "merchant_id": self.merchant_id,
            "subscriber_number": subscriber_number,
            "r-switch": self.get_provider_code(provider_name),
            "customer_email": email,
        }

            # -----------------------------
            # MAKE REQUEST TO PAYMENT GATEWAY
            # -----------------------------
        try:
            response = requests.post(
                f"{self.BASE_URL}/transaction/process",
                auth=self.auth,
                headers=self.headers,
                json=body,
                # timeout=30,
            )
            # response.raise_for_status()  # raise exception if HTTP 4xx/5xx

            try:
                response_json = response.json()
            except ValueError:
                return {
                    "status": False,
                    "message": "Invalid JSON response from payment provider",
                    "data": None,
                }

        except (requests.exceptions.RequestException, AssertionError) as e:
            # Network errors / gateway down
            return {
                "status": False,
                "message": f"Payment request failed: {str(e)}",
                "data": None,
            }

        # -----------------------------
        # HANDLE PAYMENT STATUS
        # -----------------------------
        status_value = str(response_json.get("status", "")).lower()

        match status_value:
            case "approved":
                return {
                    "status": True,
                    "message": "Payment successful",
                    "data": response_json,
                }

            case "declined":
                return {
                    "status": False,
                    "message": "Payment declined",
                    "data": response_json,
                }
            case _:
                return {
                    "status": False,
                    "message": "Payment failed",
                    "data": response_json,
                }
                    
                    
                