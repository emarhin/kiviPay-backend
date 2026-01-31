import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from datetime import datetime

from paychannel.models import PaymentChannel
from payment.models import Payment
from payment.paystack import PaystackMobileMoney

from drf_spectacular.utils import extend_schema, OpenApiExample

# In-memory session store (use Redis in production)
USSD_SESSIONS = {}


def ussd_response(session_id, message, continue_session, msisdn):
    return JsonResponse({
        "sessionID": session_id,
        "message": message,
        "continueSession": continue_session,
        "msisdn": msisdn,
    })




def ussd_response(session_id: str, message: str, continue_session: bool, msisdn: str) -> JsonResponse:
    """
    Construct a standard USSD response.

    Args:
        session_id (str): Unique session identifier for the USSD transaction.
        message (str): Message to be displayed to the user.
        continue_session (bool): Whether to keep the USSD session alive.
        msisdn (str): The phone number of the user.

    Returns:
        JsonResponse: JSON formatted USSD response.
    """
    return JsonResponse({
        "sessionID": session_id,
        "message": message,
        "continueSession": continue_session,
        "msisdn": msisdn,
    })


@extend_schema(
    summary="USSD Payment Handler",
    description=(
        "This endpoint handles USSD requests for mobile money payments.\n\n"
        "Flow:\n"
        "1. User dials USSD code → new session created.\n"
        "2. Confirm or cancel payment.\n"
        "3. Initiate Paystack MoMo charge.\n"
        "4. Prompt for OTP if required.\n"
        "5. Submit OTP to Paystack for verification."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "sessionID": {"type": "string", "description": "Unique USSD session ID"},
                "msisdn": {"type": "string", "description": "User phone number"},
                "userData": {"type": "string", "description": "USSD input or OTP"},
                "network": {"type": "string", "description": "Network provider (default: MTN)"},
                "userID": {"type": "string", "description": "Optional user ID"},
                "newSession": {"type": "boolean", "description": "Flag indicating new USSD session"},
            },
            "example": {
                "sessionID": "17698868701279400",
                "msisdn": "233555268315",
                "userData": "*928*144*1#",
                "network": "MTN",
                "userID": "ESBCSVMTCO_MlhZP",
                "newSession": True
            }
        }
    },
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
    tags=["USSD Payments"],
)
@api_view(["POST"])
@csrf_exempt
def ussd_handler(request):
    # Parse JSON request
    data = json.loads(request.body.decode("utf-8"))
    print("USSD REQUEST:", data)

    session_id = data.get("sessionID")
    msisdn = data.get("msisdn")
    user_data = (data.get("userData") or "").strip()
    network = (data.get("network") or "mtn").lower()
    userID = data.get("userID")
    new_session = data.get("newSession") is True or str(data.get("newSession")).lower() == "true"

    # -------------------------------
    # NEW SESSION → USSD *CODE*
    # -------------------------------
    if new_session:
        if not user_data.startswith("*") or "*" not in user_data:
            return ussd_response(session_id, "Invalid USSD format", False, msisdn)

        # Extract last part of USSD string as channel code
        channel_code = user_data.replace("#", "").split("*")[-1]

        try:
            channel = PaymentChannel.objects.get(ussd=channel_code, ussd_enabled=True)
        except PaymentChannel.DoesNotExist:
            return ussd_response(session_id, "Invalid payment channel", False, msisdn)

        # Initialize session
        USSD_SESSIONS[session_id] = {
            "level": 1,
            "channel_id": str(channel.id),
            "reference": None,
            "awaiting_otp": False,
        }

        return ussd_response(
            session_id,
            f"{channel.name}\nAmount: GHS {channel.amount}\n1. Confirm\n2. Cancel",
            True,
            msisdn,
        )

    # -------------------------------
    # EXISTING SESSION
    # -------------------------------
    session = USSD_SESSIONS.get(session_id)
    if not session:
        return ussd_response(session_id, "Session expired. Dial again.", False, msisdn)

    # -------------------------------
    # OTP ENTRY
    # -------------------------------
    if session.get("awaiting_otp"):
        otp = user_data
        reference = session.get("reference")

        if not otp or not otp.isdigit():
            return ussd_response(session_id, "Invalid OTP. Enter the OTP sent to your phone:", True, msisdn)

        # Submit OTP to Paystack
        paystack = PaystackMobileMoney()
        result = paystack.submit_otp(otp=otp, reference=reference)
        print("OTP RESPONSE:", result)

        # Remove session
        USSD_SESSIONS.pop(session_id, None)

        if result.get("status") is True:
            return ussd_response(session_id, "OTP submitted successfully.\nAwait payment confirmation.", False, msisdn)
        else:
            return ussd_response(session_id, "OTP verification failed.\nTransaction cancelled.", False, msisdn)

    # -------------------------------
    # CONFIRM PAYMENT
    # -------------------------------
    if session["level"] == 1:
        if user_data == "2":
            USSD_SESSIONS.pop(session_id, None)
            return ussd_response(session_id, "Transaction cancelled.", False, msisdn)

        if user_data != "1":
            return ussd_response(session_id, "Invalid option\n1. Confirm\n2. Cancel", True, msisdn)

        channel = PaymentChannel.objects.get(id=session["channel_id"])
        reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        paystack = PaystackMobileMoney()
        response = paystack.charge(
            email=f"{msisdn}-{userID}@{network}.com",
            amount=int(channel.amount),
            currency="GHS",
            provider_name="MTN",
            phone=msisdn,
            reference=reference,
            metadata={"source": "ussd", "channel": channel.name},
        )
        print("PAYSTACK RESPONSE:", response)

        # Store payment
        Payment.objects.create(
            channel=channel,
            amount=channel.amount,
            phone_number=msisdn,
            reference=reference,
            charge_type="momo",
            channel_type="ussd",
            status="pending",
        )

        # -------------------------------
        # Handle send_otp response
        # -------------------------------
        data = response.get("data", {})
        if data.get("status") == "send_otp":
            session["reference"] = reference
            session["awaiting_otp"] = True
            USSD_SESSIONS[session_id] = session

            return ussd_response(session_id, "Enter the OTP sent to your phone:", True, msisdn)

        # Remove session after initiation
        USSD_SESSIONS.pop(session_id, None)

        if response.get("status") is True:
            return ussd_response(session_id, "Payment initiated.\nApprove on your phone.", False, msisdn)

        return ussd_response(session_id, "Payment failed. Try again later.", False, msisdn)
