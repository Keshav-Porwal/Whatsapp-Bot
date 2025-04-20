from fastapi import APIRouter, Request
from app.services.gemini_api import chat_with_gemini, analyze_crop_image
from app.services.whatsapp_api import send_whatsapp_message, send_image_analysis_result
from app.services.mongo_db import save_user, save_message
from fastapi.responses import PlainTextResponse
from fastapi import Form
from pydantic import BaseModel
import requests
import base64

router = APIRouter()

@router.post("/chat")
async def handle_text_chat(req: Request):
    data = await req.json()
    user_id = data.get("user_id")
    message = data.get("message")
    user_name = data.get("user_name", "")

    if not user_id or not message:
        return {"error": "user_id and message are required"}

    save_user(user_id, user_name)
    save_message(user_id, message, is_bot=False)

    reply = chat_with_gemini(message)

    save_message(user_id, reply, is_bot=True)

    return {
        "user_id": user_id,
        "reply": reply
    }

class ImageRequest(BaseModel):
    user_id: str
    base64_image: str
    user_name: str = ""

@router.post("/upload-image")
async def handle_image_upload(payload: ImageRequest):
    save_user(payload.user_id, payload.user_name)
    save_message(payload.user_id, "[Image Uploaded]", is_bot=False)

    diagnosis = analyze_crop_image(payload.base64_image)

    save_message(payload.user_id, diagnosis, is_bot=True)

    return {
        "user_id": payload.user_id,
        "diagnosis": diagnosis
    }


@router.post("/webhook")
async def webhook(req: Request):
    form = await req.form()

    # Extract WhatsApp message and sender details
    message = form.get("Body", "")  # 'Body' contains the message text
    phone_number = form.get("From", "")  # 'From' contains the sender's phone number

    # Process text message using Gemini API
    if message:
        save_user(phone_number, "")
        save_message(phone_number, message, is_bot=False)

        # Get response from Gemini
        reply = chat_with_gemini(message)

        # Save bot response and send it back via WhatsApp
        save_message(phone_number, reply, is_bot=True)
        send_whatsapp_message(phone_number, reply)

    # Process image (crop diagnosis)
    if form.get("MediaUrl0"):  # Checking if image URL exists
        image_url = form["MediaUrl0"]
        
        # Download image and convert to base64
        response = requests.get(image_url)
        image_base64 = base64.b64encode(response.content).decode('utf-8')

        # Get crop disease diagnosis
        diagnosis = analyze_crop_image(image_base64)

        # Save and send diagnosis
        save_message(phone_number, diagnosis, is_bot=True)
        send_image_analysis_result(phone_number, diagnosis)

    return {"status": "success"}