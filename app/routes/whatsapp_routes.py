from fastapi import APIRouter, Request
from app.services.mongo_db import get_recent_messages, save_user, save_message
from app.services.gemini_api import chat_with_gpt, analyze_crop_image, get_user_session_info
from app.services.whatsapp_api import send_whatsapp_message
from app.services.generate_questions import generate_Questions
from app.services.follow_up_handler import follow_up_handler
from app.utils.helper import extract_phone_number, format_whatsapp_message, download_twilio_media
import base64

router = APIRouter()

def check_direct_call_request(message: str) -> bool:
    """
    Check if user is directly requesting a call without any prior voice bot prompt.
    Returns True if user wants to initiate a voice call.
    """
    message_lower = message.lower().strip()
    
    # English call request patterns
    english_patterns = [
        'call me', 'call kar', 'call karo', 'call please', 
        'phone call', 'voice call', 'baat karna chahiye', 
        'call back', 'ring me', 'phone karo', 'call now'
    ]
    
    # Hindi call request patterns  
    hindi_patterns = [
        'कॉल करें', 'कॉल कर', 'कॉल करो', 'फोन करें', 
        'फोन करो', 'बात करना चाहिए', 'बात करना है',
        'आवाज़ में बात', 'voice में बात', 'बोल कर बताएं',
        'कॉल पर बात', 'फोन पर बात', 'call करें', 'call करो'
    ]
    
    # Check for direct call patterns
    for pattern in english_patterns + hindi_patterns:
        if pattern in message_lower:
            return True
    
    return False

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
            'KHETI AI EXPERT' in msg.get('message', '')):
            return True

    return False

async def initiate_direct_voice_call(user_id: str, phone_number: str, user_message: str) -> bool:
    """
    Initiate voice call immediately when user directly requests it.
    """
    try:
        # Send immediate acknowledgment
        ack_message = (
            "📞 **कॉल शुरू हो रही है!** (Call starting!)\n\n"
            "🎙️ **आपकी कॉल 30 सेकंड में आएगी:**\n"
            "• फोन की रिंग का इंतज़ार करें\n"
            "• अपनी समस्या स्पष्ट रूप से बताएं\n"
            "• हिंदी या English में बात कर सकते हैं\n\n"
            "⏳ **कृपया प्रतीक्षा करें...**"
        )
        
        send_whatsapp_message(phone_number, ack_message)
        save_message(user_id, ack_message, "", True, "")
        
        # Format phone number for API
        formatted_phone = f"0{phone_number.replace('+91', '').replace('+', '')}"
        
        # Prepare API call data with enhanced system message
        api_url = "http://115.112.107.166:8081/api/make_call"
        
        # Get recent conversation context for better voice bot interaction
        recent_messages = get_recent_messages(user_id, limit=10)
        conversation_context = ""
        
        for msg in recent_messages[-5:]:  # Last 5 messages for context
            if msg.get('message'):
                role = "User" if not msg.get('is_bot', False) else "Bot"
                conversation_context += f"{role}: {msg.get('message', '')[:100]}...\n"
        
        system_message = f"""You are KHETI AI EXPERT, an advanced agricultural assistant voice bot for Indian farmers. You speak Hindi and English fluently.

FARMER CONTEXT:
- Phone: {phone_number}
- Direct Call Request: "{user_message}"
- Recent Context: {conversation_context}

YOUR ROLE:
🌾 Expert agricultural consultant specializing in Indian crops
🎯 Friendly, patient, and solution-focused
📱 Connected to WhatsApp for follow-up support

CONVERSATION APPROACH:
1. Warm greeting + acknowledge their call request
2. Ask about their specific crop problem
3. Gather key details: crop type, symptoms, field size, location
4. Provide immediate actionable advice
5. Mention WhatsApp follow-up with detailed solutions

REMEMBER:
- Be conversational and empathetic
- Ask one question at a time
- Give practical, local solutions
- Use Hindi-English mix as comfortable for farmers
- Keep responses under 30 seconds each
- Mention WhatsApp support for detailed treatment plans

Start with: "Namaste! Main aapka KHETI AI EXPERT hun. Aapne call ki request ki thi - main yahan hun aapki madad ke liye!"
"""

        call_data = {
            "phone_number": formatted_phone,
            "system_message": system_message
        }
        
        print(f"[DIRECT_CALL] Initiating call to {formatted_phone}")
        
        # Make API call
        import requests
        response = requests.post(api_url, json=call_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DIRECT_CALL] API Response: {result}")
            
            success_message = (
                "✅ **कॉल Successfully शुरू हुई!**\n"
                "📞 आपका फोन बजेगा\n"
                "🤖 KHETI AI EXPERT से बात करें\n\n"
                "💡 **कॉल के बाद आपको मिलेगा:**\n"
                "• Detailed treatment plan\n" 
                "• Product recommendations\n"
                "• Step-by-step solutions"
            )
            
            send_whatsapp_message(phone_number, success_message)
            save_message(user_id, success_message, "", True, "")
            
            return True
        else:
            raise Exception(f"API call failed: {response.status_code}")
            
    except Exception as e:
        print(f"[DIRECT_CALL] Error: {str(e)}")
        
        # Send error message
        error_message = (
            "❌ **कॉल में तकनीकी समस्या**\n\n"
            "🔄 **वैकल्पिक तरीके:**\n"
            "• 5 मिनट बाद 'call करें' लिख कर भेजें\n"
            "• अपनी फसल की फोटो भेजें\n"
            "• समस्या टेक्स्ट में लिखें\n\n"
            "📞 **Direct Call**: +91 85188 00080"
        )
        
        send_whatsapp_message(phone_number, error_message)
        save_message(user_id, error_message, "", True, "")
        
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
        
        # Generate diagnostic questions based on conversation history
        diagnostic_questions = await generate_Questions(user_id)
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(diagnostic_questions)])
        
        # Prepare system message with crop context and generated questions
        system_message = f"""You are AgriBot, an AI agricultural assistant specializing in crop disease diagnosis and product recommendations.

CONVERSATION CONTEXT:
Crop type: {crop_type if crop_type else 'Not specified'}
Recent farmer queries: {conversation_context[:800] if conversation_context else 'Image analysis completed'}

DIAGNOSTIC QUESTIONS TO ASK:
{questions_text}

YOUR ROLE & INSTRUCTIONS:
1. First, greet the farmer warmly in Hindi
2. Introduce yourself as AgriBot designed to help with crop disease diagnosis
3. Start asking the diagnostic questions one by one to understand their crop problem better
4. Based on their answers, provide specific crop disease diagnosis and treatment recommendations
5. If they ask for product recommendations, look up current agricultural products and suggest specific brands/medicines available in India
6. Speak primarily in Hindi with English technical terms where necessary (जैसे fertilizer, pesticide, fungicide etc.)
7. Be conversational, empathetic, and practical in your approach
8. Focus on actionable solutions and product recommendations

COMMUNICATION STYLE:
- Use Hindi as primary language with English technical terms
- Be warm and understanding of farmer's concerns  
- Ask follow-up questions if needed for better diagnosis
- Provide specific product names and application methods
- Keep responses concise but comprehensive

Start by greeting them and then systematically work through the diagnostic questions to help them effectively."""
        
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
                "📞 कॉल सफलतापूर्वक शुरू हो गई!\n"
                "📲 कृपया फोन उठाएं।"
            )
            send_whatsapp_message(phone_number, success_msg)
            save_message(user_id, success_msg, "", True, crop_type)
            
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

async def get_treatment_progress(user_id: str, phone_number: str) -> str:
    """
    Get treatment progress and provide guidance based on conversation history.
    """
    try:
        # Get recent messages to find voice call summaries and treatments
        recent_messages = get_recent_messages(user_id, limit=20)
        
        voice_call_summaries = []
        treatment_messages = []
        last_analysis = None
        
        for msg in recent_messages:
            message_text = msg.get('message', '')
            crop_type = msg.get('crop_type', '')
            
            if crop_type == 'voice_call_summary':
                voice_call_summaries.append({
                    'message': message_text,
                    'timestamp': msg.get('timestamp', ''),
                    'date': msg.get('timestamp', '')[:10] if msg.get('timestamp') else 'Unknown'
                })
            elif 'उपचार' in message_text or 'treatment' in message_text.lower():
                treatment_messages.append(message_text[:200])
            elif 'Analysis Report' in message_text or 'समस्या का समाधान' in message_text:
                last_analysis = message_text[:300]
        
        if voice_call_summaries:
            latest_call = voice_call_summaries[0]  # Most recent
            progress_msg = f"""📊 **आपका Treatment Progress Report**

🎙️ **Last Voice Call**: {latest_call['date']}
📝 **Total Consultations**: {len(voice_call_summaries)} voice calls + {len(treatment_messages)} text treatments

📋 **Progress Check करने के लिए बताएं**:
• फसल की मौजूदा स्थिति कैसी है? (बेहतर/वैसी ही/और खराब)
• दी गई दवाइयों का छिड़काव किया या नहीं?
• कोई नए लक्षण दिखे हैं क्या?
• अब तक कितना पैसा खर्च हुआ?

🔍 **Next Steps के लिए**:
• Current photos भेजें updated analysis के लिए
• 'call करें' लिखें expert से detailed बात के लिए
• Specific problems हों तो directly लिखें

💡 **Tip**: Regular updates देते रहने से बेहतर results मिलते हैं!

📞 **Urgent Help**: +91 85188 00080"""
        
        elif last_analysis:
            progress_msg = f"""📊 **Treatment Follow-up Required**

📝 **आपका पिछला Analysis**: {last_analysis}...

🔄 **Progress Update के लिए**:
• अपनी फसल की current photos भेजें
• Treatment के बाद क्या changes दिखे हैं?
• 'call करें' लिखकर detailed discussion करें

📱 **Quick Actions**:
• 'उपचार' - step-by-step treatment guide
• 'दवा' - medicine recommendations  
• 'help' - immediate assistance"""
        
        else:
            progress_msg = f"""📊 **Progress Tracking शुरू करें**

💬 **अभी तक कोई treatment record नहीं मिला**

🚀 **शुरुआत करने के लिए**:
• अपनी फसल की problem की photos भेजें
• 'call करें' लिखकर voice consultation लें
• अपनी समस्या text में लिखें

📈 **Progress tracking benefits**:
• Treatment effectiveness monitor करना
• Cost और time savings
• Better results के लिए adjustments

📞 **Expert Consultation**: +91 85188 00080"""
        
        return progress_msg
        
    except Exception as e:
        print(f"[PROGRESS] Error getting progress for {user_id}: {str(e)}")
        return f"""📊 **Progress Check**

❌ Technical issue in fetching your treatment history.

🔄 **Please try**:
• Send fresh crop photos for new analysis
• Type 'call करें' for voice consultation
• Write your current problem in text

📞 **Direct Help**: +91 85188 00080"""

async def send_post_call_summary(user_id: str, phone_number: str, transcript_data: dict):
    """
    Send intelligent summary and solutions after voice call completion.
    """
    try:
        from datetime import datetime
        
        # Extract conversation from transcript
        conversation = transcript_data.get('call_conversation', [])
        call_duration = int(transcript_data.get('call_duration', 0))
        
        if not conversation:
            return False
        
        # Parse conversation if it's a JSON string
        if isinstance(conversation, str):
            import json
            try:
                conversation = json.loads(conversation)
            except json.JSONDecodeError:
                print("[POST_CALL] Error parsing conversation JSON")
                return False
        
        # Prepare conversation text for AI analysis
        conversation_text = ""
        user_messages = []
        bot_messages = []
        
        for msg in conversation:
            role = msg.get('role', '')
            content = msg.get('content', '').strip()
            
            if content and content not in ['noise', '<noise>', '']:
                if role == 'user':
                    conversation_text += f"किसान: {content}\n"
                    user_messages.append(content)
                elif role == 'assistant':
                    conversation_text += f"बॉट: {content}\n"
                    bot_messages.append(content)
        
        if not user_messages:
            print("[POST_CALL] No valid user messages found")
            return False
        
        # Generate AI-powered summary and solutions
        summary_prompt = f"""
आप एक expert agricultural consultant हैं। नीचे दी गई voice conversation का comprehensive analysis करके practical solution दें।

VOICE CONVERSATION:
{conversation_text}

CALL DETAILS:
- अवधि: {call_duration} सेकंड
- संदेशों की संख्या: {len(conversation)}
- किसान के सवाल: {len(user_messages)}

कृपया इस format में structured response दें:

## 🔍 समस्या का सारांश (Problem Summary):
[2-3 lines में मुख्य समस्या बताएं - फसल, disease, गंभीरता]

## 💡 मुख्य बातें (Key Discussion Points):
• पहली मुख्य बात
• दूसरी मुख्य बात  
• तीसरी मुख्य बात

## 🌿 तत्काल समाधान (Immediate Solutions):

### जैविक उपचार (Organic Treatment):
• **नीम तेल**: 15ml/लीटर पानी, शाम को छिड़काव
• **साबुन पानी**: 5ml liquid soap/लीटर, रोज़ाना
• **लहसुन स्प्रे**: 50g लहसुन + 10 मिर्च/लीटर पानी

### रासायनिक उपचार (Chemical Treatment):
• **[Brand Name]**: [Active ingredient] - [exact dosage]/एकड़
• **[Brand Name]**: [Active ingredient] - [exact dosage]/एकड़
• छिड़काव समय: शाम 4-6 बजे, 7-10 दिन का अंतर

## 💊 खरीदारी सूची (Shopping List):
• **नीम तेल**: ₹250-350/लीटर (कृषि दुकान)
• **[Chemical 1]**: ₹[price]/[size] - [company name]
• **[Chemical 2]**: ₹[price]/[size] - [company name]

## 📅 7-दिन कार्य योजना:
**Day 1-2**: पहला छिड़काव + प्रभावित area की सफाई
**Day 3-4**: monitoring और दूसरा छिड़काव (यदि जरूरी हो)
**Day 5-7**: परिणाम की जांच + तीसरा छिड़काव

## ⚠️ सावधानियां:
• मास्क व दस्ताने जरूर पहनें
• बारिश से पहले छिड़काव न करें
• सुबह 10 बजे के बाद छिड़काव न करें

कृपया specific Indian brand names, exact dosages, और practical advice दें जो farmer तुरंत implement कर सके।
"""

        # Get AI analysis
        ai_summary, _ = await chat_with_gpt(summary_prompt, user_id)
        
        # Create comprehensive follow-up message
        summary_message = f"""📞 **आपकी Voice Call का पूरा समाधान**

⏱️ **कॉल अवधि**: {call_duration//60} मिनट {call_duration%60} सेकंड
💬 **बातचीत**: {len(user_messages)} सवाल, {len(bot_messages)} जवाब

{ai_summary}

📱 **अगले कदम (Next Steps)**:
• इस solution को screenshot कर के save करें
• दवाई खरीदने से पहले दुकानदार को यह message दिखाएं
• 'progress' लिखकर treatment का हाल बताएं
• समस्या हो तो 'help' या 'call करें' लिखें

📞 **24x7 Support**: +91 85188 00080
🔄 **Follow-up**: 3 दिन बाद update जरूर करें

✅ **यह solution आपकी voice conversation के आधार पर AI expert द्वारा तैयार किया गया है**
"""

        # Send the comprehensive summary in chunks
        summary_chunks = format_whatsapp_message(summary_message, max_length=1500)
        
        for i, chunk in enumerate(summary_chunks):
            if len(summary_chunks) > 1:
                chunk_with_indicator = f"📋 Voice Call Report ({i+1}/{len(summary_chunks)})\n{chunk}"
            else:
                chunk_with_indicator = f"📋 Voice Call Complete Report\n{chunk}"
                
            send_whatsapp_message(phone_number, chunk_with_indicator)
            
            # Save each chunk to database
            save_message(user_id, chunk, "", True, "voice_call_summary")
        
        print(f"[POST_CALL] Comprehensive summary sent to {phone_number}, duration: {call_duration}s, messages: {len(user_messages)}")
        return True
        
    except Exception as e:
        print(f"[POST_CALL] Error sending summary to {phone_number}: {str(e)}")
        
        # Send basic completion message if AI analysis fails
        fallback_msg = f"""📞 **Voice Call सफलतापूर्वक समाप्त!**

⏱️ **कॉल अवधि**: {call_duration//60 if 'call_duration' in locals() else 0} मिनट
✅ आपकी समस्याओं पर detailed चर्चा हुई

🔄 **तत्काल करें**:
• अपनी फसल की latest photo भेजें analysis के लिए
• 'उपचार' लिखें step-by-step treatment के लिए
• 'दवा' लिखें medicine की जानकारी के लिए
• Urgent help के लिए 'call करें' लिखें

📞 **Direct Expert Help**: +91 85188 00080
💚 **हमेशा आपकी सेवा में - KHETI AI Team**"""

        send_whatsapp_message(phone_number, fallback_msg)
        save_message(user_id, fallback_msg, "", True, "voice_call_complete")
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

            # Check if user is directly requesting a call (NEW FEATURE)
            if check_direct_call_request(message):
                # Save user request
                save_message(user_id, message, "", False, "")
                
                # Trigger immediate voice call without confirmation
                call_triggered = await initiate_direct_voice_call(user_id, phone_number, message)
                if call_triggered:
                    return {"status": "success", "action": "direct_call_initiated"}

            # Check if user is requesting progress update (NEW FEATURE)
            if message.lower().strip() in ['progress', 'प्रोग्रेस', 'स्टेटस', 'status', 'update', 'हाल']:
                # Get recent call summaries and provide progress tracking
                progress_message = await get_treatment_progress(user_id, phone_number)
                send_whatsapp_message(phone_number, progress_message)
                save_message(user_id, progress_message, "", True, "progress_update")
                return {"status": "success", "action": "progress_update"}

            # Check if this is a follow-up message (treatment/prevention/medicine)
            should_handle_followup, detected_intent = follow_up_handler.should_handle_message(user_id, message)
            
            if should_handle_followup and detected_intent:
                # Get context from recent analysis
                analysis_info = follow_up_handler.get_last_analysis_info(user_id)
                
                # Generate targeted response
                follow_up_response = follow_up_handler.generate_response(
                    intent=detected_intent,
                    crop_type=analysis_info.get("crop_type", ""),
                    disease=analysis_info.get("disease", ""),
                    user_id=user_id
                )
                
                # Save user message
                save_message(user_id, message, "", False, analysis_info.get("crop_type", ""))
                
                # Send follow-up response in chunks if needed
                response_chunks = format_whatsapp_message(follow_up_response, max_length=1500)
                
                for i, chunk in enumerate(response_chunks):
                    # Save bot response
                    save_message(user_id, chunk, "", True, analysis_info.get("crop_type", ""))
                    
                    # Add chunk indicator for multi-part messages
                    if len(response_chunks) > 1:
                        chunk_with_indicator = f"({i+1}/{len(response_chunks)})\n{chunk}"
                    else:
                        chunk_with_indicator = chunk
                    
                    send_whatsapp_message(phone_number, chunk_with_indicator)
                
                return {"status": "success", "type": "follow_up", "intent": detected_intent}

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
            
            # Occasionally suggest voice call feature for complex problems
            elif session_info and session_info.get("message_count", 0) > 5 and session_info.get("message_count", 0) % 7 == 0:
                call_hint_msg = (
                    "💡 **Quick Tip**: जटिल समस्याओं के लिए\n"
                    "📞 'call करें' लिखकर Voice Expert से बात करें!\n"
                    "🎙️ तत्काल समाधान + WhatsApp follow-up"
                )
                send_whatsapp_message(phone_number, call_hint_msg)

        # ---------------- IMAGE MESSAGE HANDLING WITH SESSION MANAGEMENT ----------------
        elif media_url:
            try:
                # Save user with phone number
                save_user(user_id, phone_number, "")

                # Send acknowledgment
                ack_message = "📸 फोटो मिल गई! समाधान हो रहा है...\n(Image received! Analyzing...)"
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
                    "🌟 **आपकी समस्या का समाधान मिल गया है!** "

                    "\n🎯 **और भी जानकारी चाहिए? यहाँ टाइप करें:**"

                    "\n💊 **विस्तृत उपचार के लिए** (For detailed treatment):"
                    "\n• 'उपचार' या 'treatment'"
                    "\n• 'इलाज' या 'detailed solution'"

                    "\n🛡️ **भविष्य में बचाव के लिए** (For future prevention):"
                    "\n• 'रोकथाम' या 'prevention'"
                    "\n• 'बचाव' या 'protection'"

                    "\n🧪 **दवा की पूरी जानकारी के लिए** (For complete medicine information):"
                    "\n• 'दवा' या 'medicine'"
                    "\n• 'कीटनाशक' या 'pesticide'"

                    "\n🧮 **खुराक कैलकुलेटर के लिए** (For dosage calculator):"
                    "\n• 'खुराक' या 'dosage'"
                    "\n• 'मात्रा' या 'quantity'"

                    "\n💰 **लागत की जानकारी के लिए** (For cost information):"
                    "\n• 'कीमत' या 'cost'"
                    "\n• 'लागत' या 'budget'"

                    "\n🌾 **फसल प्रबंधन के लिए** (For crop management):"
                    "\n• 'प्रबंधन' या 'management'"
                    "\n• 'देखभाल' या 'care'"

                    "\n⏰ **समय सारणी के लिए** (For schedule):"
                    "\n• 'समय' या 'timing'"
                    "\n• 'कैलेंडर' या 'calendar'"

                    "\n🆘 **आपातकाल के लिए** (For emergency):"
                    "\n• 'तुरंत' या 'urgent'"
                    "\n• 'आपातकाल' या 'emergency'"

                    "\n📞 **व्यक्तिगत सलाह:** +91 85188 00080"

                    "\n✨ **बस टाइप करें और पूरी जानकारी पाएं!** (Just type and get complete information!)"
                )
                send_whatsapp_message(phone_number, follow_up_msg)
                
                # Save follow-up message to database
                save_message(user_id, follow_up_msg, "", True, crop_type)

                # Let's ask the farmer for the Voice-Bot assistance
                voice_bot_msg = (
                    "\n🎙️क्या आप KHETI AI EXPERT से बात करना चाहेंगे?\n"
                    "अपनी समस्या बताएं, मैं आपकी मदद करूंगा!"
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


@router.post("/test-direct-call")
async def test_direct_call_feature(phone_number: str, test_message: str = "call करें"):
    """
    Test endpoint for the new direct call feature.
    """
    try:
        # Clean phone number
        clean_phone = phone_number.replace('+', '')
        if clean_phone.startswith('91'):
            clean_phone = clean_phone[2:]
        
        user_id = clean_phone
        
        # Test direct call detection
        is_direct_call = check_direct_call_request(test_message)
        
        if is_direct_call:
            # Simulate the direct call process
            call_result = await initiate_direct_voice_call(user_id, phone_number, test_message)
            
            return {
                "status": "success",
                "message": f"Direct call feature test completed",
                "phone_number": phone_number,
                "test_message": test_message,
                "detected_as_call_request": True,
                "call_initiated": call_result,
                "feature_working": True
            }
        else:
            return {
                "status": "success", 
                "message": "Message not detected as call request",
                "phone_number": phone_number,
                "test_message": test_message,
                "detected_as_call_request": False,
                "suggestion": "Try messages like: 'call करें', 'call me', 'फोन करो', 'बात करना है'"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "phone_number": phone_number,
            "test_message": test_message
        }


@router.get("/call-patterns")
async def get_call_patterns():
    """
    Get all supported patterns for direct call requests.
    """
    return {
        "direct_call_feature": {
            "description": "Users can now request calls directly without waiting for bot prompts",
            "supported_patterns": {
                "english": [
                    "call me", "call kar", "call karo", "call please", 
                    "phone call", "voice call", "baat karna chahiye", 
                    "call back", "ring me", "phone karo", "call now"
                ],
                "hindi": [
                    "कॉल करें", "कॉल कर", "कॉल करो", "फोन करें", 
                    "फोन करो", "बात करना चाहिए", "बात करना है",
                    "आवाज़ में बात", "voice में बात", "बोल कर बताएं",
                    "कॉल पर बात", "फोन पर बात", "call करें", "call करो"
                ]
            },
            "how_it_works": [
                "1. User types any call request phrase",
                "2. System immediately detects intent", 
                "3. Sends acknowledgment message",
                "4. Initiates voice call within 30 seconds",
                "5. Enhanced system message with conversation context",
                "6. Post-call AI analysis and WhatsApp follow-up"
            ],
            "test_endpoint": "/test-direct-call?phone_number=+91XXXXXXXXXX&test_message=call करें"
        }
    }

@router.post("/test-post-call-summary")
async def test_post_call_summary(phone_number: str):
    """
    Test the comprehensive post-call summary system with sample data.
    """
    try:
        # Clean phone number
        clean_phone = phone_number.replace('+', '')
        if clean_phone.startswith('91'):
            clean_phone = clean_phone[2:]
        
        # Sample transcript data (realistic conversation)
        sample_transcript = {
            "dialer_id": "0",
            "did_no": phone_number,
            "client_no": "416102",
            "customer_attended": "1", 
            "call_time": "2025-10-12T15:30:00+05:30",
            "call_conversation": [
                {"role": "user", "content": "नमस्ते, मेरी मिर्ची में समस्या है"},
                {"role": "assistant", "content": "नमस्ते! मैं आपका कृषि सहायक हूँ। आपकी मिर्ची में क्या समस्या है?"},
                {"role": "user", "content": "पत्तियों पर सफेद जाले हैं और पत्तियां पीली होकर सूख रही हैं। 5 एकड़ में लगी है।"},
                {"role": "assistant", "content": "यह स्पाइडर माइट्स की समस्या लगती है। कब से यह समस्या है?"},
                {"role": "user", "content": "15-20 दिन से है। पहले थोड़ी थी अब बहुत बढ़ गई है।"},
                {"role": "assistant", "content": "आपने कोई दवा डाली है अब तक?"},
                {"role": "user", "content": "हाँ, Abamectin डाली थी 1 हफ्ते पहले लेकिन कोई फायदा नहीं हुआ।"},
                {"role": "assistant", "content": "Abamectin अब प्रभावी नहीं है। आपको Spiromesifen या Propargite का उपयोग करना चाहिए। साथ में नीम तेल भी मिलाएं।"},
                {"role": "user", "content": "कितनी मात्रा में डालना है और कहाँ मिलेगा?"},
                {"role": "assistant", "content": "Spiromesifen 1ml प्रति लीटर पानी में। कृषि दुकान से मिल जाएगा। शाम को छिड़काव करें।"}
            ],
            "recording_url": "https://calls2.ivrsolutions.in/monitor/sample.wav",
            "call_duration": "240",
            "recordid": "TEST123"
        }
        
        # Test the comprehensive summary system
        result = await send_post_call_summary(clean_phone, phone_number, sample_transcript)
        
        return {
            "status": "success",
            "message": "Post-call summary test completed",
            "phone_number": phone_number,
            "user_id": clean_phone,
            "summary_sent": result,
            "sample_conversation_length": len(sample_transcript['call_conversation']),
            "call_duration": sample_transcript['call_duration'] + " seconds",
            "features_tested": [
                "AI conversation analysis",
                "Problem identification", 
                "Organic + Chemical solutions",
                "Product recommendations with brands",
                "Shopping list with prices",
                "7-day treatment plan",
                "Safety warnings",
                "WhatsApp message chunking",
                "Database saving",
                "Progress tracking setup"
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "phone_number": phone_number
        }

@router.get("/test-voice-bot/{phone_number}")
async def test_voice_bot_endpoint(phone_number: str):
    """Test endpoint to directly test voice bot API"""
    result = await test_voice_bot_api(phone_number)
    return {"success": result, "phone": phone_number}