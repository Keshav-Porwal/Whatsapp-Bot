from fastapi import APIRouter, Request
from app.services.mongo_db import get_recent_messages, save_user, save_message
from app.services.gemini_api import chat_with_gpt, analyze_crop_image, get_user_session_info
from app.services.whatsapp_api import send_whatsapp_message
from app.utils.helper import extract_phone_number, format_whatsapp_message, download_twilio_media
import base64

router = APIRouter()

def check_voice_bot_request(user_id: str, current_message: str) -> bool:
    """
    Check if user replied 'yes' to the voice bot question.
    Returns True if the last bot message was voice_bot_msg and user replied yes.
    """
    # Normalize user response
    user_response = current_message.lower().strip()

    # Check for positive responses in English and Hindi
    positive_responses = ['yes', 'y', 'हाँ', 'हां', 'han', 'haan', 'ok', 'okay']

    if user_response not in positive_responses:
        return False

    # Get last 5 messages to check conversation context (increased for better detection)
    recent_messages = get_recent_messages(user_id, limit=5)

    if len(recent_messages) < 2:
        return False

    # Look for voice bot question in recent messages
    for msg in reversed(recent_messages):
        if (msg.get('is_bot', False) and 
            '🎙️' in msg.get('message', '') and 
            'Voice-Bot' in msg.get('message', '')):
            return True

    return False

async def test_voice_bot_api(phone_number: str):
    """
    Test function to check if voice bot API is working
    Call this function directly to test the API
    """
    import requests
    import asyncio
    
    # Format phone number (add prefix 0 as required by API)
    formatted_phone = f"0{phone_number.replace('+91', '').replace('+', '')}"
    
    # API payload for testing
    payload = {
        "Voicechat_id": "yBDtN5156Agk",
        "ai_agent_ext": 416102,
        "customer_no": formatted_phone,
        "text": "This is a test call from WhatsApp bot. Testing voice bot functionality.",
        "system_msg": "You are a test voice bot. Keep the conversation short and confirm that the call is working.",
        "connect_ws_after_answer": False,
        "timezone": "Asia/Kolkata"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer 9dd1de37f1bf4ba5a1367760a6539a9b"  # ⚠️ REPLACE THIS
    }
    
    try:
        print(f"🧪 Testing Voice Bot API for: {formatted_phone}")
        print(f"📞 Original phone: {phone_number}")
        print(f"📋 Payload: {payload}")
        
        response = requests.post(
            "https://api.ivrsolutions.in/api/dial_by_voicebot",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"✅ Status: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

async def handle_voice_bot_call(user_id: str, phone_number: str, crop_type: str, message: str):
    """
    Handle voice bot API call if user agreed to voice bot assistance.
    Only calls API if check_voice_bot_request returns True.
    """
    import requests
    import asyncio
    
    # Check if this is a positive response to voice bot question
    if not check_voice_bot_request(user_id, message):
        return False
    
    try:
        # Send confirmation message
        confirmation_msg = (
            "🎙️ Voice-Bot call shuru kar raha hun!\n"
            "Kuch seconds mein aapko call aayegi.\n"
            "Starting Voice-Bot call! You'll receive a call shortly."
        )
        send_whatsapp_message(phone_number, confirmation_msg)
        save_message(user_id, confirmation_msg, "", True, crop_type)
        
        # Save user's positive response first
        save_message(user_id, message, "", False, crop_type)
        
        # Prepare API call data
        api_url = "https://api.ivrsolutions.in/api/dial_by_voicebot"
        
        # Format phone number (add prefix 0 as required by API)
        formatted_phone = f"0{phone_number.replace('+91', '').replace('+', '')}"
        print(f"Formatted phone number for API: {formatted_phone}")
        
        # Get recent conversation context for the system message
        recent_messages = get_recent_messages(user_id, limit=5)
        conversation_context = ""
        
        for msg in recent_messages:
            if not msg.get('is_bot', False) and msg.get('message', '').strip():
                conversation_context = msg.get('message', '')
                break
        
        # Prepare system message with crop context
        system_message = f"""You are an AI agricultural assistant helping a farmer. 
        The farmer has shared crop issues and received analysis.
        Crop type: {crop_type if crop_type else 'Not specified'}
        Recent user query: {conversation_context[:200] if conversation_context else 'Image analysis completed'}
        Speak in Hindi and English mix. Be helpful and provide agricultural guidance."""
        
        # API payload
        payload = {
            "Voicechat_id": "yBDtN5156Agk",  # Replace with your actual voicechat ID
            "ai_agent_ext": 416102,  # Replace with your AI agent extension
            "customer_no": formatted_phone,
            "text": "Namaste! Main aapka Krishi Sahayak Voice-Bot hun. Aap apni fasal ki samasya bata sakte hain. Hello! I'm your Agricultural Assistant Voice-Bot. You can tell me about your crop problems.",
            "system_msg": system_message,
        }
        
        # API headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 9dd1de37f1bf4ba5a1367760a6539a9b"
        }
        
        # Debug logging
        print(f"=== VOICE BOT API CALL DEBUG ===")
        print(f"API URL: {api_url}")
        print(f"Original phone: {phone_number}")
        print(f"Formatted phone: {formatted_phone}")
        print(f"Payload: {payload}")
        print(f"Headers: {headers}")
        print("================================")
        
        # Make the API call
        print(f"Initiating voice bot call for {phone_number} (formatted: {formatted_phone})")
        
        # Use asyncio to make the request non-blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(api_url, json=payload, headers=headers, timeout=30)
        )
        
        print(f"=== API RESPONSE DEBUG ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        print("===========================")
        
        # Handle API response
        if response.status_code == 200:
            success_msg = (
                "✅ Voice-Bot call successfully started!\n"
                "Aapko call aa rahi hogi. Kripya phone uthayiye.\n"
                "Call should be coming to you now. Please answer the phone."
            )
            send_whatsapp_message(phone_number, success_msg)
            save_message(user_id, success_msg, "", True, crop_type)
            
            # Additional instruction message
            instruction_msg = (
                "📞 Voice-Bot se baat karne ke liye:\n"
                "• Saaf aur dhire boliye\n"
                "• Apni problem detail mein batayiye\n"
                "• Call khatam hone ke baad WhatsApp par bhi message kar sakte hain\n\n"
                "Tips for Voice-Bot conversation:\n"
                "• Speak clearly and slowly\n"
                "• Describe your problem in detail\n"
                "• You can continue on WhatsApp after the call"
            )
            send_whatsapp_message(phone_number, instruction_msg)
            save_message(user_id, instruction_msg, "", True, crop_type)
            
            return True
            
        else:
            # Handle API errors
            error_response = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_message = error_response.get('message', 'Unknown error occurred')
            
            if response.status_code == 400:
                error_msg = f"❌ Call parameters mein problem: {error_message}"
            elif response.status_code == 405:
                error_msg = f"❌ API access denied: {error_message}"
            elif response.status_code == 500:
                error_msg = f"❌ Server problem: {error_message}"
            else:
                error_msg = f"❌ Voice-Bot call mein problem (Code: {response.status_code}): {error_message}"
            
            send_whatsapp_message(phone_number, error_msg)
            save_message(user_id, error_msg, "", True, crop_type)
            
            # Offer alternative support
            fallback_msg = (
                "🔄 Voice-Bot call nahi ho saka. Koi baat nahi!\n"
                "Aap yahan WhatsApp par apni problem puch sakte hain.\n"
                "Main text mein bhi madad kar sakta hun.\n\n"
                "Voice-Bot call failed. No worries!\n"
                "You can ask your questions here on WhatsApp.\n"
                "I can help you via text as well."
            )
            send_whatsapp_message(phone_number, fallback_msg)
            save_message(user_id, fallback_msg, "", True, crop_type)
            
            return False
            
    except requests.exceptions.Timeout:
        timeout_msg = "❌ Voice-Bot service mein delay. Thodi der baad try kariye."
        send_whatsapp_message(phone_number, timeout_msg)
        save_message(user_id, timeout_msg, "", True, crop_type)
        return False
        
    except requests.exceptions.RequestException as e:
        network_msg = f"❌ Network problem: {str(e)[:100]}"
        send_whatsapp_message(phone_number, network_msg)
        save_message(user_id, network_msg, "", True, crop_type)
        return False
        
    except Exception as e:
        error_msg = f"❌ Voice-Bot call mein technical problem: {str(e)[:100]}"
        send_whatsapp_message(phone_number, error_msg)
        save_message(user_id, error_msg, "", True, crop_type)
        print(f"Voice bot API error for {phone_number}: {str(e)}")
        return False

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

            # Check if user is responding to voice bot question and handle API call
            voice_bot_handled = await handle_voice_bot_call(user_id, phone_number, "", message)
            if voice_bot_handled:
                return {"status": "success"}

            # Get AI response with crop type (includes session management)
            reply, crop_type = await chat_with_gpt(message, user_id)

            # Save user message to database
            save_message(user_id, message, "", False, crop_type)

            # Format and send response in properly sized chunks
            message_chunks = format_whatsapp_message(reply, max_length=1500)
            
            for i, chunk in enumerate(message_chunks):
                # Save each bot reply chunk to database
                save_message(user_id, chunk, "", True, crop_type)
                
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
                save_message(user_id, ack_message, "", True, "")

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
                save_message(user_id, "", image_base64, False, crop_type)
                
                # Format and send diagnosis in proper chunks
                diagnosis_chunks = format_whatsapp_message(diagnosis, max_length=1500)
                
                for i, chunk in enumerate(diagnosis_chunks):
                    # Save each diagnosis chunk to database
                    save_message(user_id, chunk, "", True, crop_type)
                    
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
                save_message(user_id, follow_up_msg, "", True, crop_type)

                # Let's ask the farmer for the Voice-Bot assistance
                voice_bot_msg = (
                    "\n🎙️ Kya aap Voice-Bot se baat karna chahenge?\n"
                    "Aap apni problem bol sakte hain aur main madad karunga!\n"
                    "Would you like to try the Voice-Bot? You can speak your problem and I'll assist!"
                )
                send_whatsapp_message(phone_number, voice_bot_msg)
                save_message(user_id, voice_bot_msg, "", True, crop_type)

            except Exception as e:
                error_msg = f"❌ Photo processing mein problem: {str(e)[:100]}..."
                print(f"Image processing error for {phone_number}: {str(e)}")
                send_whatsapp_message(phone_number, error_msg)
                
                # Save error message to database
                save_message(user_id, error_msg, "", True, "")

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
            save_message(user_id, help_msg, "", True, "")

        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/test-voice-bot/{phone_number}")
async def test_voice_bot_endpoint(phone_number: str):
    """Test endpoint to directly test voice bot API"""
    result = await test_voice_bot_api(phone_number)
    return {"success": result, "phone": phone_number}