from fastapi import APIRouter, Request, Form, HTTPException
from app.services.mongo_db import save_user, save_message
from app.services.gemini_api import (  # Updated import
    chat_with_gpt, 
    analyze_crop_image, 
    get_treatment_followup,
    extract_crop_type_from_ai_response,
    get_user_session_info,
    clear_user_conversation,
    get_active_sessions_count,
    get_all_sessions_info
)
from app.services.whatsapp_api import send_whatsapp_message
from app.models import TextChatRequest, ImageRequest, TreatmentRequest
from app.utils.helper import extract_phone_number, format_whatsapp_message, download_twilio_media
from app.config import settings
import base64
import os

# Environment variables with validation
TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN

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

# ---------------------------- ENHANCED TEXT CHAT ENDPOINT WITH SESSION MANAGEMENT ----------------------------

@router.post("/chat")
async def handle_text_chat(req: TextChatRequest):
    """Enhanced text chat with session management and proper message saving"""
    try:
        # Validate input
        if not req.user_id or not req.message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        # Save user (only once, prevents duplicates)
        save_user(req.user_id, "", req.user_name or "")

        # Get AI response with crop type (this now includes session management)
        reply, crop_type = await chat_with_gpt(req.message, req.user_id)

        # Save user message to database
        user_crop_type = extract_crop_type_from_ai_response(req.message) if not crop_type else crop_type
        save_message(
            user_id=req.user_id,
            message=req.message,
            is_bot=False,
            crop_type=user_crop_type
        )

        # Save bot reply to database
        save_message(
            user_id=req.user_id,
            message=reply,
            is_bot=True,
            crop_type=crop_type
        )

        # Get session info
        session_info = get_user_session_info(req.user_id)

        return {
            "user_id": req.user_id,
            "reply": reply,
            "crop_type": crop_type if crop_type else "Not identified",
            "session_info": {
                "message_count": session_info.get("message_count", 0) if session_info else 0,
                "time_remaining": session_info.get("time_remaining", 0) if session_info else 0
            }
        }

    except Exception as e:
        error_reply = f"⚠️ Kuch problem hui hai. Phir se try kariye. (Error: {str(e)})"
        # Save error message too
        save_message(
            user_id=req.user_id,
            message=error_reply,
            is_bot=True,
            crop_type=""
        )
        return {
            "user_id": req.user_id,
            "reply": error_reply,
            "error": True
        }

# ---------------------------- ENHANCED IMAGE UPLOAD ENDPOINT WITH SESSION MANAGEMENT ----------------------------

@router.post("/upload-image")
async def handle_image_upload(payload: ImageRequest):
    """Enhanced image analysis with session management and proper message saving"""
    try:
        # Validate input
        if not payload.user_id or not payload.base64_image:
            raise HTTPException(status_code=400, detail="user_id and base64_image are required")

        # Save user (only once)
        save_user(payload.user_id, "", payload.user_name or "")

        # Enhanced image analysis with session management
        diagnosis, crop_type = await analyze_crop_image(
            payload.base64_image, 
            payload.user_id  # Now includes session management
        )

        # Save image upload to database (store base64 instead of message)
        save_message(
            user_id=payload.user_id,
            message="",  # Empty message for image
            image_base64=payload.base64_image,
            is_bot=False,
            crop_type=crop_type
        )

        # Save diagnosis to database
        save_message(
            user_id=payload.user_id,
            message=diagnosis,
            is_bot=True,
            crop_type=crop_type
        )

        # Get session info
        session_info = get_user_session_info(payload.user_id)

        return {
            "user_id": payload.user_id,
            "diagnosis": diagnosis,
            "crop_type": crop_type if crop_type else "Not identified",
            "session_info": {
                "message_count": session_info.get("message_count", 0) if session_info else 0,
                "time_remaining": session_info.get("time_remaining", 0) if session_info else 0
            }
        }

    except Exception as e:
        error_msg = f"⚠️ Image analysis mein problem: {str(e)}"
        save_message(
            user_id=payload.user_id,
            message=error_msg,
            is_bot=True,
            crop_type=""
        )
        return {
            "user_id": payload.user_id,
            "diagnosis": error_msg,
            "error": True
        }

# ---------------------------- TREATMENT FOLLOW-UP ENDPOINT WITH SESSION MANAGEMENT ----------------------------

@router.post("/treatment-details")
async def get_treatment_details(req: TreatmentRequest):
    """Get detailed treatment information with session context"""
    try:
        # Get detailed treatment guidance with session context
        treatment_details = get_treatment_followup(req.disease, req.crop, req.user_id)
        
        # Save interaction to database
        save_message(
            user_id=req.user_id,
            message=f"Treatment request: {req.disease} in {req.crop}",
            is_bot=False,
            crop_type=req.crop
        )
        save_message(
            user_id=req.user_id,
            message=treatment_details,
            is_bot=True,
            crop_type=req.crop
        )
        
        # Get session info
        session_info = get_user_session_info(req.user_id)
        
        return {
            "user_id": req.user_id,
            "disease": req.disease,
            "crop": req.crop,
            "treatment_details": treatment_details,
            "session_info": {
                "message_count": session_info.get("message_count", 0) if session_info else 0,
                "time_remaining": session_info.get("time_remaining", 0) if session_info else 0
            }
        }
        
    except Exception as e:
        error_msg = f"Treatment info mein problem: {str(e)}"
        save_message(
            user_id=req.user_id,
            message=error_msg,
            is_bot=True,
            crop_type=req.crop
        )
        return {
            "user_id": req.user_id,
            "error": error_msg
        }

# ---------------------------- ENHANCED WHATSAPP WEBHOOK WITH SESSION MANAGEMENT ----------------------------

@router.post("/webhook")
async def webhook(req: Request):
    """Enhanced WhatsApp webhook with session management and proper message saving"""
    try:
        # Parse form data
        form = await req.form()
        
        # Extract information
        body_field = form.get("Body", "")
        if isinstance(body_field, str):
            message = body_field.strip()
        else:
            message = ""
        from_field = form.get("From", "")
        if not isinstance(from_field, str):
            from_field = str(from_field)
        phone_number = extract_phone_number(from_field)
        media_url = form.get("MediaUrl0")
        
        if not phone_number:
            return {"status": "error", "message": "No phone number provided"}

        # Use phone number as user_id for WhatsApp users
        user_id = phone_number
        
        # ---------------- TEXT MESSAGE HANDLING WITH SESSION MANAGEMENT ----------------
        if message and not media_url:
            # Save user with phone number
            save_user(user_id, phone_number, "")

            # Get AI response with crop type (includes session management)
            reply, crop_type = await chat_with_gpt(message, user_id)

            # Save user message to database
            save_message(
                user_id=user_id,
                message=message,
                is_bot=False,
                crop_type=crop_type
            )

            # Format and send response in properly sized chunks
            message_chunks = format_whatsapp_message(reply, max_length=1500)
            
            for i, chunk in enumerate(message_chunks):
                # Save each bot reply chunk to database
                save_message(
                    user_id=user_id,
                    message=chunk,
                    is_bot=True,
                    crop_type=crop_type
                )
                
                # Add message number indicator for multi-part messages
                if len(message_chunks) > 1:
                    chunk_indicator = f"({i+1}/{len(message_chunks)})\n{chunk}"
                else:
                    chunk_indicator = chunk
                    
                send_whatsapp_message(phone_number, chunk_indicator)

            # Send session info to user if it's a long conversation
            session_info = get_user_session_info(user_id)
            if session_info and session_info.get("message_count", 0) > 20:
                session_msg = f"💬 Session: {session_info.get('message_count', 0)} messages, {session_info.get('time_remaining', 0)//60:.0f} min remaining"
                send_whatsapp_message(phone_number, session_msg)

        # ---------------- IMAGE MESSAGE HANDLING WITH SESSION MANAGEMENT ----------------
        elif media_url:
            try:
                # Save user with phone number
                save_user(user_id, phone_number, "")

                # Send acknowledgment
                ack_message = "📸 Photo mil gayi! Analysis ho raha hai...\n(Image received! Analyzing...)"
                send_whatsapp_message(phone_number, ack_message)
                
                # Save acknowledgment message to database
                save_message(
                    user_id=user_id,
                    message=ack_message,
                    is_bot=True,
                    crop_type=""
                )

                # Download image with improved authentication
                try:
                    if not isinstance(media_url, str):
                        media_url_str = str(media_url)
                    else:
                        media_url_str = media_url
                    image_content = download_twilio_media(media_url_str)
                    print(f"Successfully downloaded image for {phone_number}, size: {len(image_content)} bytes")
                except Exception as download_error:
                    print(f"Image download error for {phone_number}: {str(download_error)}")
                    raise download_error

                # Convert to base64
                image_base64 = base64.b64encode(image_content).decode('utf-8')
                print(f"Image converted to base64 for {phone_number}, length: {len(image_base64)}")

                # Analyze image with context and session management
                diagnosis, crop_type = await analyze_crop_image(image_base64, user_id)
                
                # Save image upload to database (store base64 instead of message text)
                save_message(
                    user_id=user_id,
                    message="",  # Empty message for image uploads
                    image_base64=image_base64,
                    is_bot=False,
                    crop_type=crop_type
                )
                
                # Format and send diagnosis in proper chunks
                diagnosis_chunks = format_whatsapp_message(diagnosis, max_length=1500)
                
                for i, chunk in enumerate(diagnosis_chunks):
                    # Save each diagnosis chunk to database
                    save_message(
                        user_id=user_id,
                        message=chunk,
                        is_bot=True,
                        crop_type=crop_type
                    )
                    
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
                
                # Save follow-up message to database
                save_message(
                    user_id=user_id,
                    message=follow_up_msg,
                    is_bot=True,
                    crop_type=crop_type
                )

            except Exception as e:
                error_msg = f"❌ Photo processing mein problem: {str(e)[:100]}..."
                print(f"Image processing error for {phone_number}: {str(e)}")
                send_whatsapp_message(phone_number, error_msg)
                
                # Save error message to database
                save_message(
                    user_id=user_id,
                    message=error_msg,
                    is_bot=True,
                    crop_type=""
                )

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
            
            # Save help message to database
            save_user(user_id, phone_number, "")
            save_message(
                user_id=user_id,
                message=help_msg,
                is_bot=True,
                crop_type=""
            )

        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

# ---------------------------- SESSION MANAGEMENT ENDPOINTS ----------------------------

@router.get("/session/{user_id}")
async def get_session_info(user_id: str):
    """Get session information for a specific user"""
    session_info = get_user_session_info(user_id)
    if session_info:
        return {
            "user_id": user_id,
            "session_info": session_info
        }
    else:
        return {
            "user_id": user_id,
            "session_info": None,
            "message": "No active session found"
        }

@router.delete("/session/{user_id}")
async def clear_session(user_id: str):
    """Clear a user's session"""
    success = clear_user_conversation(user_id)
    return {
        "user_id": user_id,
        "cleared": success,
        "message": "Session cleared" if success else "No active session to clear"
    }

@router.get("/sessions/stats")
async def get_sessions_stats():
    """Get statistics about all active sessions"""
    stats = get_all_sessions_info()
    return {
        "active_sessions": get_active_sessions_count(),
        "stats": stats
    }

# ---------------------------- DEBUGGING ENDPOINTS ----------------------------

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
            "from_env_token_length": len(os.getenv("TWILIO_AUTH_TOKEN") or "") if os.getenv("TWILIO_AUTH_TOKEN") else 0
        }
    }

@router.get("/debug/sessions")
async def debug_sessions():
    """Debug endpoint to check session manager status"""
    return {
        "session_manager_status": "active",
        "active_sessions": get_active_sessions_count(),
        "all_sessions": get_all_sessions_info()
    }