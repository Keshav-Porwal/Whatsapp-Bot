from fastapi import APIRouter, Request, Form, HTTPException
from app.services.mongo_db import update_user_context, get_user_context
from app.services.gemini_api import (
    chat_with_gpt, 
    analyze_crop_image, 
    get_treatment_followup,
    context_manager
)
from app.services.whatsapp_api import send_whatsapp_message
from app.services.mongo_db import save_user, save_message
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import requests
import base64
import os
import re
from typing import Optional

# Environment variables with validation
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC7a11efa7925fea0a4030c86cf2098811")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "0e1b19cb689baa4fe98452398d31dc96")

# Debug credentials on startup
print(f"[STARTUP] Twilio credentials check:")
print(f"[STARTUP] ACCOUNT_SID: {'Present' if TWILIO_ACCOUNT_SID else 'MISSING'}")
print(f"[STARTUP] AUTH_TOKEN: {'Present' if TWILIO_AUTH_TOKEN else 'MISSING'}")
if TWILIO_ACCOUNT_SID:
    print(f"[STARTUP] SID format: {TWILIO_ACCOUNT_SID[:8]}... ({'Valid' if TWILIO_ACCOUNT_SID.startswith('AC') else 'INVALID - should start with AC'})")
if TWILIO_AUTH_TOKEN:
    print(f"[STARTUP] Token length: {len(TWILIO_AUTH_TOKEN)}")

# Create router
router = APIRouter()

# Enhanced Pydantic models
class TextChatRequest(BaseModel):
    user_id: str
    message: str
    user_name: str = ""
    location: Optional[str] = None
    crop_type: Optional[str] = None

class ImageRequest(BaseModel):
    user_id: str
    base64_image: str
    user_name: str = ""
    location: Optional[str] = None
    additional_info: Optional[str] = ""

class TreatmentRequest(BaseModel):
    user_id: str
    disease: str
    crop: str

# Helper functions
def extract_phone_number(from_field: str) -> str:
    """Extract clean phone number from WhatsApp format"""
    # Remove 'whatsapp:' prefix if present
    phone = from_field.replace('whatsapp:', '').strip()
    return phone

def is_hindi_english_mixed(text: str) -> bool:
    """Check if text contains Hindi characters"""
    hindi_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(hindi_pattern.search(text))

def format_whatsapp_message(message: str, max_length: int = 1500) -> list:
    """Smart message formatting for WhatsApp with Twilio limits"""
    # Twilio's actual limit is 1600 characters, but we use 1500 for safety
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    
    # First try to split by double newlines (paragraphs/sections)
    sections = message.split('\n\n')
    current_chunk = ""
    
    for section in sections:
        # If adding this section exceeds limit
        if len(current_chunk + '\n\n' + section) > max_length:
            # Save current chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If section itself is too long, split it further
            if len(section) > max_length:
                # Split by single newlines
                lines = section.split('\n')
                temp_chunk = ""
                for line in lines:
                    if len(temp_chunk + '\n' + line) > max_length:
                        if temp_chunk.strip():
                            chunks.append(temp_chunk.strip())
                        temp_chunk = line
                    else:
                        temp_chunk += '\n' + line if temp_chunk else line
                
                if temp_chunk.strip():
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = section
        else:
            current_chunk += '\n\n' + section if current_chunk else section
    
    # Add any remaining content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Final check - if any chunk is still too long, split by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
        else:
            # Split by sentences (. or ! or ?)
            sentences = []
            temp_sentences = chunk.replace('!', '.').replace('?', '.').split('.')
            for sent in temp_sentences:
                if sent.strip():
                    sentences.append(sent.strip() + '.')
            
            temp_chunk = ""
            for sentence in sentences:
                if len(temp_chunk + ' ' + sentence) > max_length:
                    if temp_chunk.strip():
                        final_chunks.append(temp_chunk.strip())
                    temp_chunk = sentence
                else:
                    temp_chunk += ' ' + sentence if temp_chunk else sentence
            
            if temp_chunk.strip():
                final_chunks.append(temp_chunk.strip())
    
    return final_chunks if final_chunks else [message[:max_length]]

def download_twilio_media(media_url: str) -> bytes:
    """Download media from Twilio with proper authentication"""
    try:
        # Debug: Check if credentials are loaded
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise ValueError(f"Missing credentials: SID={'Present' if TWILIO_ACCOUNT_SID else 'Missing'}, Token={'Present' if TWILIO_AUTH_TOKEN else 'Missing'}")
        
        print(f"[DEBUG] Using Account SID: {TWILIO_ACCOUNT_SID[:8]}...")
        print(f"[DEBUG] Token length: {len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 0}")
        print(f"[DEBUG] Media URL: {media_url}")
        
        # Validate that SID starts with 'AC' (Twilio Account SID format)
        if not TWILIO_ACCOUNT_SID.startswith('AC'):
            raise ValueError(f"Invalid Account SID format. Should start with 'AC', got: {TWILIO_ACCOUNT_SID[:5]}...")
        
        # Method 1: Basic authentication with requests.auth
        response = requests.get(
            media_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30,
            headers={
                'User-Agent': 'TwilioMediaDownloader/1.0',
                'Accept': 'image/*'
            }
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"[DEBUG] Successfully downloaded {len(response.content)} bytes")
            return response.content
        
        # If 401, the credentials are definitely wrong
        if response.status_code == 401:
            print(f"[DEBUG] Authentication failed. Response: {response.text[:500]}")
            raise ValueError(f"Twilio authentication failed. Check your ACCOUNT_SID and AUTH_TOKEN. SID: {TWILIO_ACCOUNT_SID[:8]}...")
            
        # For other status codes, try alternative method
        print(f"[DEBUG] First method failed with status {response.status_code}, trying alternative...")
        
        # Method 2: Manual Authorization header
        import base64
        credentials = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
        
        response = requests.get(
            media_url,
            headers={
                'Authorization': f'Basic {credentials}',
                'User-Agent': 'TwilioMediaDownloader/1.0',
                'Accept': 'image/*'
            },
            timeout=30
        )
        
        print(f"[DEBUG] Alternative method status: {response.status_code}")
        
        if response.status_code == 200:
            return response.content
            
        # If still failing, provide detailed error
        raise ValueError(f"Failed to download image. Status: {response.status_code}, Response: {response.text[:300]}")
        
    except requests.exceptions.Timeout:
        raise ValueError("Image download timed out after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(f"Connection error while downloading image: {str(e)}")
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        raise ValueError(f"Unexpected error during image download: {str(e)}")

# ---------------------------- ENHANCED TEXT CHAT ENDPOINT ----------------------------

@router.post("/chat")
async def handle_text_chat(req: TextChatRequest):
    """Enhanced text chat with context awareness"""
    try:
        # Validate input
        if not req.user_id or not req.message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        # Update user context with additional information
        if req.location:
            update_user_context(req.user_id, {"location": req.location})
        if req.crop_type:
            update_user_context(req.user_id, {"crop_type": req.crop_type})

        # Save user and message
        save_user(req.user_id, req.user_name)
        save_message(req.user_id, req.message, is_bot=False)

        # Get intelligent response
        reply = chat_with_gpt(req.message, req.user_id)

        # Save bot reply
        save_message(req.user_id, reply, is_bot=True)

        # Get user context for additional info
        user_context = get_user_context(req.user_id)

        return {
            "user_id": req.user_id,
            "reply": reply,
            "context": {
                "crop_type": user_context.get('crop_type'),
                "location": user_context.get('location'),
                "last_diseases": user_context.get('identified_diseases', [])[-3:]  # Last 3 diseases
            }
        }

    except Exception as e:
        return {
            "user_id": req.user_id,
            "reply": f"⚠️ Kuch problem hui hai. Phir se try kariye. (Error: {str(e)})",
            "error": True
        }

# ---------------------------- ENHANCED IMAGE UPLOAD ENDPOINT ----------------------------

@router.post("/upload-image")
async def handle_image_upload(payload: ImageRequest):
    """Enhanced image analysis with context"""
    try:
        # Validate input
        if not payload.user_id or not payload.base64_image:
            raise HTTPException(status_code=400, detail="user_id and base64_image are required")

        # Update context
        if payload.location:
            update_user_context(payload.user_id, {"location": payload.location})

        # Save user and upload event
        save_user(payload.user_id, payload.user_name)
        
        # Create descriptive message for database
        upload_msg = "[Image Uploaded]"
        if payload.additional_info:
            upload_msg += f" - {payload.additional_info}"
        
        save_message(payload.user_id, upload_msg, is_bot=False)

        # Enhanced image analysis
        diagnosis = analyze_crop_image(
            payload.base64_image, 
            payload.user_id
        )

        # Save diagnosis
        save_message(payload.user_id, diagnosis, is_bot=True)

        # Get updated context
        user_context = get_user_context(payload.user_id)

        return {
            "user_id": payload.user_id,
            "diagnosis": diagnosis,
            "context": {
                "crop_type": user_context.get('crop_type'),
                "confidence": "Check diagnosis for confidence level",
                "follow_up_available": True
            }
        }

    except Exception as e:
        error_msg = f"⚠️ Image analysis mein problem: {str(e)}"
        save_message(payload.user_id, error_msg, is_bot=True)
        return {
            "user_id": payload.user_id,
            "diagnosis": error_msg,
            "error": True
        }

# ---------------------------- TREATMENT FOLLOW-UP ENDPOINT ----------------------------

@router.post("/treatment-details")
async def get_treatment_details(req: TreatmentRequest):
    """Get detailed treatment information for diagnosed diseases"""
    try:
        # Get detailed treatment guidance
        treatment_details = get_treatment_followup(req.disease, req.crop, req.user_id)
        
        # Save interaction
        save_message(req.user_id, f"Treatment request: {req.disease} in {req.crop}", is_bot=False)
        save_message(req.user_id, treatment_details, is_bot=True)
        
        return {
            "user_id": req.user_id,
            "disease": req.disease,
            "crop": req.crop,
            "treatment_details": treatment_details
        }
        
    except Exception as e:
        return {
            "user_id": req.user_id,
            "error": f"Treatment info mein problem: {str(e)}"
        }

# ---------------------------- ENHANCED WHATSAPP WEBHOOK ----------------------------

@router.post("/webhook")
async def webhook(req: Request):
    """Enhanced WhatsApp webhook with intelligent conversation handling"""
    try:
        # Parse form data
        form = await req.form()
        
        # Extract information
        message = form.get("Body", "").strip()
        phone_number = extract_phone_number(form.get("From", ""))
        media_url = form.get("MediaUrl0")
        
        if not phone_number:
            return {"status": "error", "message": "No phone number provided"}

        # Initialize/update user context
        
        
        # ---------------- TEXT MESSAGE HANDLING ----------------
        if message and not media_url:
            # Save incoming message
            save_user(phone_number, "")
            save_message(phone_number, message, is_bot=False)

            # Check if this is location/context information
            if any(keyword in message.lower() for keyword in ['location', 'state', 'district', 'village']):
                update_user_context(phone_number, {"location": message})
                response_prefix = "📍 Location save ho gaya. "
            else:
                response_prefix = ""

            # Get AI response with context
            context = await get_user_context(phone_number)
            reply = chat_with_gpt(message, phone_number)
            print(f"[DEBUG] Context before reply: {context}")
            full_reply = response_prefix + reply

            # Format and send response in properly sized chunks
            message_chunks = format_whatsapp_message(full_reply, max_length=1500)
            
            for i, chunk in enumerate(message_chunks):
                save_message(phone_number, chunk, is_bot=True)
                
                # Add message number indicator for multi-part messages
                if len(message_chunks) > 1:
                    chunk_indicator = f"({i+1}/{len(message_chunks)})\n{chunk}"
                else:
                    chunk_indicator = chunk
                    
                send_whatsapp_message(phone_number, chunk_indicator)

        # ---------------- IMAGE MESSAGE HANDLING ----------------
        elif media_url:
            try:
                # Save image upload event first
                image_msg = "[Fasal ki photo mili / Crop Image Received]"
                if message:  # If there's accompanying text
                    image_msg += f" - {message}"
                    
                save_user(phone_number, "")
                save_message(phone_number, image_msg, is_bot=False)

                # Send acknowledgment
                send_whatsapp_message(
                    phone_number, 
                    "📸 Photo mil gayi! Analysis ho raha hai...\n(Image received! Analyzing...)"
                )

                # Download image with improved authentication
                try:
                    image_content = download_twilio_media(media_url)
                    print(f"Successfully downloaded image for {phone_number}, size: {len(image_content)} bytes")
                except Exception as download_error:
                    print(f"Image download error for {phone_number}: {str(download_error)}")
                    raise download_error

                # Convert to base64
                image_base64 = base64.b64encode(image_content).decode('utf-8')
                print(f"Image converted to base64 for {phone_number}, length: {len(image_base64)}")

                # Analyze image with context
                diagnosis = analyze_crop_image(image_base64, phone_number)
                
                # Format and send diagnosis in proper chunks
                diagnosis_chunks = format_whatsapp_message(diagnosis, max_length=1500)
                
                for i, chunk in enumerate(diagnosis_chunks):
                    save_message(phone_number, chunk, is_bot=True)
                    
                    if len(diagnosis_chunks) > 1:
                        chunk_with_indicator = f"📋 Report ({i+1}/{len(diagnosis_chunks)})\n{chunk}"
                    else:
                        chunk_with_indicator = f"📋 Fasal Analysis Report:\n{chunk}"
                        
                    send_whatsapp_message(phone_number, chunk_with_indicator)

                # Send follow-up options
                follow_up_msg = (
                    "\n💬 Aur jaankari ke liye puchiye:\n"
                    "• 'treatment' - detailed ilaj\n"
                    "• 'prevention' - future bachav\n"
                    "• 'medicine' - dawa ki jaankari\n\n"
                    "Ask for more info:\n"
                    "• 'उपचार' or 'treatment'\n"
                    "• 'रोकथाम' or 'prevention'\n"
                    "• 'दवा' or 'medicine'"
                )
                send_whatsapp_message(phone_number, follow_up_msg)

            except Exception as e:
                error_msg = f"❌ Photo processing mein problem: {str(e)[:100]}..."
                print(f"Image processing error for {phone_number}: {str(e)}")
                send_whatsapp_message(phone_number, error_msg)
                
                # Also save the error to database
                save_message(phone_number, f"Error: {str(e)}", is_bot=True)

        # If neither text nor image
        else:
            help_msg = (
                "🌾 *Krishi Sahayak Bot*\n\n"
                "Main aapki fasal ki problem mein madad kar sakta hun:\n"
                "📸 Fasal ki photo bhejiye\n"
                "💬 Apni problem likhiye\n"
                "📍 Apna location bataiye\n\n"
                "*Agri Help Bot*\n"
                "I can help with crop problems:\n"
                "📸 Send crop photos\n"
                "💬 Describe your problem\n"
                "📍 Share your location"
            )
            send_whatsapp_message(phone_number, help_msg)

        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

# ---------------------------- USER CONTEXT ENDPOINT ----------------------------

@router.get("/user-context/{user_id}")
async def get_user_context(user_id: str):
    """Get user's conversation context and history"""
    try:
        context = context_manager.get_user_context(user_id)
        return {
            "user_id": user_id,
            "context": {
                "crop_type": context.get('crop_type'),
                "location": context.get('location'),
                "identified_diseases": context.get('identified_diseases', []),
                "conversation_count": len(context.get('conversation_history', [])) // 2,
                "last_analysis": context.get('last_analysis', {}).get('timestamp') if context.get('last_analysis') else None
            }
        }
    except Exception as e:
        return {"error": f"Context retrieval error: {str(e)}"}

# ---------------------------- DEBUGGING ENDPOINT ----------------------------

@router.get("/debug/credentials")
async def debug_credentials():
    """Debug endpoint to check Twilio credentials (remove in production!)"""
    return {
        "twilio_account_sid": {
            "present": bool(TWILIO_ACCOUNT_SID),
            "format_valid": TWILIO_ACCOUNT_SID.startswith('AC') if TWILIO_ACCOUNT_SID else False,
            "preview": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else None,
            "length": len(TWILIO_ACCOUNT_SID) if TWILIO_ACCOUNT_SID else 0
        },
        "twilio_auth_token": {
            "present": bool(TWILIO_AUTH_TOKEN),
            "length": len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 0
        },
        "env_check": {
            "from_env_sid": os.getenv("TWILIO_ACCOUNT_SID", "NOT_FOUND")[:8] + "..." if os.getenv("TWILIO_ACCOUNT_SID") else "NOT_FOUND",
            "from_env_token_length": len(os.getenv("TWILIO_AUTH_TOKEN", "")) if os.getenv("TWILIO_AUTH_TOKEN") else 0
        }
    }

# ---------------------------- HEALTH CHECK ENDPOINT ----------------------------

@router.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "Crop Disease AI Bot",
        "version": "2.0.0",
        "features": [
            "Intelligent conversation context",
            "Enhanced image analysis",
            "Hindi-English mixed responses",
            "Treatment follow-up",
            "WhatsApp integration"
        ]
    }