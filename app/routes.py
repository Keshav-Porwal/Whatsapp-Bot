from fastapi import APIRouter, Request
from app.services.gemini_api import chat_with_gemini, analyze_crop_image
from app.services.whatsapp_api import send_whatsapp_message, send_image_analysis_result
from app.services.mongo_db import save_user, save_message
from fastapi.responses import PlainTextResponse
from fastapi import Form
from pydantic import BaseModel
import requests
import base64
import os

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


# Create a router to define API endpoints
router = APIRouter()

# ---------------------------- TEXT CHAT ENDPOINT ----------------------------

@router.post("/chat")
async def handle_text_chat(req: Request):
    # Extract JSON data from request
    data = await req.json()
    user_id = data.get("user_id")
    message = data.get("message")
    user_name = data.get("user_name", "")

    # Ensure user_id and message are provided
    if not user_id or not message:
        return {"error": "user_id and message are required"}

    # Save user info and message to MongoDB
    save_user(user_id, user_name)
    save_message(user_id, message, is_bot=False)

    # Get response from Gemini API
    reply = chat_with_gemini(message)

    # Save bot reply to MongoDB
    save_message(user_id, reply, is_bot=True)

    # Return the response
    return {
        "user_id": user_id,
        "reply": reply
    }

# ---------------------------- IMAGE UPLOAD ENDPOINT ----------------------------

# Define request schema for image upload
class ImageRequest(BaseModel):
    user_id: str
    base64_image: str
    user_name: str = ""

@router.post("/upload-image")
async def handle_image_upload(payload: ImageRequest):
    # Save user info and image upload event
    save_user(payload.user_id, payload.user_name)
    save_message(payload.user_id, "[Image Uploaded]", is_bot=False)

    # Analyze crop image using Gemini API
    diagnosis = analyze_crop_image(payload.base64_image)

    # Save diagnosis result to DB
    save_message(payload.user_id, diagnosis, is_bot=True)

    # Return diagnosis
    return {
        "user_id": payload.user_id,
        "diagnosis": diagnosis
    }

# ---------------------------- WHATSAPP WEBHOOK ENDPOINT ----------------------------

@router.post("/webhook")
async def webhook(req: Request):
    # Parse form data from incoming WhatsApp webhook request
    form = await req.form()

    # Extract message text and sender's phone number
    message = form.get("Body", "")  # Message body
    phone_number = form.get("From", "")  # Sender's number

    # ---------------- TEXT MESSAGE HANDLING ----------------
    if message:
        # Save incoming message
        save_user(phone_number, "")
        save_message(phone_number, message, is_bot=False)

        # Get Gemini's response, instruct it to reply in paragraphs
        reply = chat_with_gemini(
            f"Please split your answer into clearly separated paragraphs (under 1500 characters) for WhatsApp:\n\n{message}"
        )

        # Split response into chunks to fit WhatsApp format
        paragraphs = [para.strip() for para in reply.split("\n\n") if para.strip()]

        # Save and send each paragraph one by one
        for para in paragraphs:
            save_message(phone_number, para, is_bot=True)
            send_whatsapp_message(phone_number, para)

    # ---------------- IMAGE MESSAGE HANDLING ----------------
    if form.get("MediaUrl0"):
        image_url = form["MediaUrl0"]

        try:
            # ✅ Add Basic Auth to download Twilio-protected media
            response = requests.get(image_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch image, status code: {response.status_code}")

            image_base64 = base64.b64encode(response.content).decode('utf-8')

            # Updated prompt for Indian farmers
            custom_prompt = (
                "You are an expert agronomist helping Indian farmers. "
                "This image is from an Indian farm. Identify any visible crop disease, explain its root causes in the Indian context, "
                "and suggest practical, affordable preventive and treatment measures specific to Indian farming conditions."
            )

            diagnosis = analyze_crop_image(image_base64, prompt=custom_prompt)

            save_message(phone_number, diagnosis, is_bot=True)

            # Split long message into parts to avoid Twilio error
            max_len = 1500
            chunks = [diagnosis[i:i+max_len] for i in range(0, len(diagnosis), max_len)]
            for part in chunks:
                send_whatsapp_message(phone_number, part)

        except Exception as e:
            error_message = f"❌ Error processing image: {str(e)}"
            print(error_message)
            send_whatsapp_message(phone_number, error_message)


    # Return a success response to WhatsApp
    return {"status": "success"}
