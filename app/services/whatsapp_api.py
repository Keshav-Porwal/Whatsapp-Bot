from twilio.rest import Client
from app.config import settings

# Twilio credentials (account SID and auth token)
TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
TWILIO_PHONE_NUMBER = settings.TWILIO_PHONE_NUMBER

# Twilio client setup
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Send message function to WhatsApp using Twilio
def send_whatsapp_message(to: str, message: str):
    # Strip any accidental whitespace
    to = to.strip()

    # Remove prefix if already included
    if to.startswith("whatsapp:"):
        to = to.replace("whatsapp:", "")

    # Final number format should be exactly: whatsapp:+91xxxxxxxxxx
    formatted_to = f"whatsapp:{to}"

    print(f"[DEBUG] Sending to: {formatted_to} | Message: {message}")  # Optional debug log

    client.messages.create(
        body=message,
        from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
        to=formatted_to
    )

# Send image analysis result to WhatsApp
def send_image_analysis_result(to: str, result: str):
    message = f"The crop diagnosis is: {result}"
    return send_whatsapp_message(to, message)
