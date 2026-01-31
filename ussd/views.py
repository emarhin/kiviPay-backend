import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datetime import datetime

from paychannel.models import PaymentChannel
from payment.models import Payment
from payment.paystack import PaystackMobileMoney

# In-memory session store (use Redis in production)
USSD_SESSIONS = {}


def ussd_response(session_id, message, continue_session, msisdn):
    return JsonResponse({
        "sessionID": session_id,
        "message": message,
        "continueSession": continue_session,
        "msisdn": msisdn,
    })


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
