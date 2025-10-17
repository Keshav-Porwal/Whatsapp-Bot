from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from typing import Dict, Any, Optional
from app.services.whatsapp_api import send_whatsapp_message
from app.services.mongo_db import save_message, get_recent_messages
from app.services.gemini_api import chat_with_gpt

router = APIRouter()

async def process_transcript_data(transcript_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process the incoming transcript data from IVR Solutions.
    
    Expected format:
    {
        "dialer_id": "0",
        "did_no": "+918044475773", 
        "client_no": "416102",
        "customer_attended": "1",
        "call_time": "2025-10-10T20:00:52+05:30",
        "call_conversation": [...],  # Array of conversation messages
        "recording_url": "https://...",
        "call_duration": "170",
        "call_type": "outgoing"
    }
    """
    try:
        print(f"[PROCESS] Processing transcript for call: {transcript_data.get('recordid', 'Unknown')}")
        
        # Extract key information
        client_no = transcript_data.get('client_no', '')
        customer_phone = transcript_data.get('did_no', '')
        call_duration = int(transcript_data.get('call_duration', 0))
        call_time = transcript_data.get('call_time', '')
        conversation = transcript_data.get('call_conversation', [])
        recording_url = transcript_data.get('recording_url', '')
        
        # Parse conversation JSON string if it's a string
        if isinstance(conversation, str):
            try:
                conversation = json.loads(conversation)
            except json.JSONDecodeError:
                print("[PROCESS] Error parsing conversation JSON")
                conversation = []
        
        # Extract user messages and bot responses
        user_messages = []
        bot_responses = []
        
        for msg in conversation:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user' and content.strip():
                user_messages.append(content.strip())
            elif role == 'assistant' and content.strip():
                bot_responses.append(content.strip())
        
        # Create summary
        processed_summary = {
            "call_info": {
                "client_no": client_no,
                "customer_phone": customer_phone, 
                "call_duration_seconds": call_duration,
                "call_time": call_time,
                "recording_url": recording_url
            },
            "conversation_summary": {
                "total_messages": len(conversation),
                "user_messages_count": len(user_messages),
                "bot_responses_count": len(bot_responses),
                "user_messages": user_messages,
                "bot_responses": bot_responses
            },
            "analysis": {
                "call_completed": transcript_data.get('customer_attended', '0') == '1',
                "duration_minutes": round(call_duration / 60, 2),
                "conversation_quality": "good" if len(user_messages) > 2 else "limited"
            },
            "original_conversation": conversation  # Include full conversation for AI analysis
        }
        
        # Send comprehensive AI-powered follow-up WhatsApp message
        if customer_phone and len(user_messages) > 0:
            # Import the new comprehensive summary function
            from app.routes.whatsapp_routes import send_post_call_summary
            
            # Clean phone number for user_id
            clean_phone = customer_phone.replace('+', '')
            if clean_phone.startswith('91'):
                clean_phone = clean_phone[2:]
            
            # Send comprehensive summary using the original transcript data
            await send_post_call_summary(clean_phone, customer_phone, transcript_data)
        
        return processed_summary
        
    except Exception as e:
        print(f"[PROCESS] Error processing transcript: {str(e)}")
        return {
            "error": str(e),
            "raw_data": transcript_data
        }


async def generate_ai_analysis(conversation: list) -> Dict[str, Any]:
    """
    Use ChatGPT-4o to analyze the entire conversation and generate sophisticated response.
    """
    try:
        # Prepare conversation text for AI analysis
        conversation_text = ""
        for msg in conversation:
            role = msg.get('role', '')
            content = msg.get('content', '').strip()
            if content:
                if role == 'user':
                    conversation_text += f"किसान: {content}\n"
                elif role == 'assistant':
                    conversation_text += f"बॉट: {content}\n"
        
        # Create comprehensive analysis prompt
        analysis_prompt = f"""
You are an expert agricultural consultant analyzing a farmer's voice conversation. Provide a comprehensive, actionable solution based on the conversation below.

VOICE CONVERSATION:
{conversation_text}

Please provide response in this EXACT format (bilingual Hindi-English):

## 🔍 समस्या विश्लेषण (Problem Analysis):
• मुख्य समस्या: [Crop name + specific issue]
• गंभीरता स्तर: [Mild/Moderate/Severe]
• प्रभावित क्षेत्र: [Area affected]

## 🌿 जैविक समाधान (Organic Solutions):
• **नीम तेल स्प्रे**: 15ml/लीटर पानी, शाम को छिड़काव
• **साबुन पानी**: 5ml liquid soap/लीटर, दिन में 2 बार
• **लहसुन-मिर्च काढ़ा**: 50g लहसुन + 10g मिर्च/लीटर
• **जैविक कीटनाशक**: बायोएजेंट्स का प्रयोग

## 🧪 रासायनिक समाधान (Chemical Solutions):
### तत्काल उपचार:
• **[Product Name 1]**: [Active Ingredient] - [Dosage]/acre
• **[Product Name 2]**: [Active Ingredient] - [Dosage]/acre
### छिड़काव निर्देश:
• समय: शाम 4-6 बजे
• अंतराल: 7-10 दिन
• सावधानी: मास्क व दस्ताने पहनें

## 💊 खरीदारी सूची (Shopping List):
### जैविक उत्पाद:
• **नीम तेल**: ₹200-300/लीटर (कृषि दुकान)
• **बायो एजेंट**: ₹150-250/पैकेट
### रासायनिक उत्पाद:
• **[Brand Name 1]**: ₹[Price]/[Size] - [Company]
• **[Brand Name 2]**: ₹[Price]/[Size] - [Company]

## ⏰ 7-दिन कार्य योजना:
**दिन 1-2**: तत्काल छिड़काव और प्रभावित हिस्से का isolation
**दिन 3-5**: दूसरा छिड़काव और monitoring
**दिन 6-7**: परिणाम assessment और next steps

## 🛡️ रोकथाम रणनीति:
• साप्ताहिक निरीक्षण
• proper spacing और drainage
• crop rotation और field hygiene

Please be specific with actual product names, brands, and precise dosages. Keep response concise but comprehensive.
"""

        # Get AI analysis
        ai_response, _ = await chat_with_gpt(analysis_prompt, "ai_analyst")
        
        return {
            "ai_analysis": ai_response,
            "conversation_length": len(conversation),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[AI_ANALYSIS] Error: {str(e)}")
        return {
            "error": str(e),
            "fallback_analysis": "AI विश्लेषण में त्रुटि। कृपया मैन्युअल समीक्षा करें।"
        }


async def send_post_call_followup(phone_number: str, call_summary: Dict[str, Any]) -> None:
    """
    Send AI-powered sophisticated follow-up message after voice call completion.
    """
    try:
        # Clean phone number (remove + and country code if needed)
        clean_phone = phone_number.replace('+', '')
        if clean_phone.startswith('91'):
            clean_phone = clean_phone[2:]  # Remove country code
        
        user_id = clean_phone  # Use phone as user_id for WhatsApp users
        
        # Get conversation data
        conversation = call_summary.get('original_conversation', [])
        call_duration = call_summary.get('analysis', {}).get('duration_minutes', 0)
        
        print(f"[AI_FOLLOWUP] Generating AI analysis for {len(conversation)} messages...")
        
        # Generate AI analysis of the conversation
        ai_analysis = await generate_ai_analysis(conversation)
        
        # Create sophisticated follow-up message with AI insights
        if 'error' not in ai_analysis:
            follow_up_message = (
                f"🎙️ **आपकी Voice-Bot कॉल का विश्लेषण तैयार है!**\n"
                f"📞 कॉल अवधि: {call_duration} मिनट\n"
                f"🤖 AI विश्लेषण रिपोर्ट:\n\n"
                f"{ai_analysis.get('ai_analysis', '')}\n\n"
                
                "� **अगले कदम (Next Steps):**\n"
                "• फसल की latest फोटो भेजें detailed analysis के लिए\n"
                "• 'उपचार' लिखें step-by-step treatment के लिए\n"
                "• 'दवा' लिखें specific medicines के लिए\n"
                "• 'कीमत' लिखें cost estimation के लिए\n\n"
                
                "� **आपातकालीन सहायता**: +91 85188 00080\n"
                "�💚 **हमेशा आपकी सेवा में - AI + Expert Support**"
            )
        else:
            # Fallback message if AI analysis fails
            follow_up_message = (
                f"🎙️ **आपकी Voice-Bot कॉल समाप्त हुई!**\n"
                f"📞 कॉल अवधि: {call_duration} मिनट\n\n"
                
                "📋 **विशेषज्ञ समीक्षा जल्द ही:**\n"
                "• हमारे experts आपकी conversation का विश्लेषण कर रहे हैं\n"
                "• 2-3 घंटे में detailed solution मिलेगा\n\n"
                
                "📲 **तत्काल सहायता के लिए:**\n"
                "• अपनी फसल की फोटो भेजें\n"
                "• 'तुरंत' लिखें emergency help के लिए\n\n"
                
                "📞 **आपातकालीन**: +91 85188 00080"
            )
        
        # Split message if too long for WhatsApp
        from app.utils.helper import format_whatsapp_message
        message_chunks = format_whatsapp_message(follow_up_message, max_length=1500)
        
        # Send WhatsApp messages
        for i, chunk in enumerate(message_chunks):
            if len(message_chunks) > 1:
                chunk_with_indicator = f"({i+1}/{len(message_chunks)})\n{chunk}"
            else:
                chunk_with_indicator = chunk
                
            send_whatsapp_message(phone_number, chunk_with_indicator)
            
            # Save each chunk to database
            save_message(
                user_id=user_id,
                message=chunk,
                is_bot=True,
                crop_type="ai_voice_analysis"
            )
        
        # Save AI analysis as separate detailed message for records
        if 'ai_analysis' in ai_analysis:
            save_message(
                user_id=user_id,
                message=f"AI Analysis: {ai_analysis['ai_analysis']}",
                is_bot=True,
                crop_type="voice_call_ai_analysis"
            )
        
        # Save call summary
        recording_url = call_summary.get('call_info', {}).get('recording_url', '')
        call_summary_text = f"Voice call AI analysis completed - Duration: {call_duration}min"
        if recording_url:
            call_summary_text += f"\nRecording: {recording_url}"
            
        save_message(
            user_id=user_id,
            message=call_summary_text,
            is_bot=True,
            crop_type="voice_call_summary"
        )
        
        print(f"[AI_FOLLOWUP] Sent sophisticated AI analysis to {phone_number}")
        
    except Exception as e:
        print(f"[AI_FOLLOWUP] Error sending AI follow-up message: {str(e)}")

@router.post("/transcript")
async def receive_transcript(request: Request):
    """
    Handle transcript data after voice bot call completion.
    This function logs all incoming data to understand the format.
    """
    try:
        # Log request details
        print("=" * 60)
        print(f"[TRANSCRIPT] Received at: {datetime.now()}")
        print(f"[TRANSCRIPT] Method: {request.method}")
        print(f"[TRANSCRIPT] URL: {request.url}")
        print("=" * 60)
        
        # Log headers
        print("[TRANSCRIPT] HEADERS:")
        content_type = ""
        for header_name, header_value in request.headers.items():
            print(f"  {header_name}: {header_value}")
            if header_name.lower() == 'content-type':
                content_type = header_value.lower()
        print(f"[TRANSCRIPT] DETECTED CONTENT-TYPE: {content_type}")
        print("-" * 40)
        
        # Log query parameters
        print("[TRANSCRIPT] QUERY PARAMETERS:")
        for param_name, param_value in request.query_params.items():
            print(f"  {param_name}: {param_value}")
        print("-" * 40)
        
        # Get raw body first (can only be read once)
        raw_body = await request.body()
        print("[TRANSCRIPT] RAW BODY:")
        print(f"  Length: {len(raw_body)} bytes")
        
        json_body = None
        form_data = None
        text_body = ""
        
        if len(raw_body) > 0:
            try:
                # Try to decode as text first
                text_body = raw_body.decode('utf-8')
                print(f"  Text Content: {text_body}")
                
                # Try to parse as JSON
                try:
                    json_body = json.loads(text_body)
                    print("[TRANSCRIPT] PARSED JSON:")
                    print(json.dumps(json_body, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print("[TRANSCRIPT] Not valid JSON format")
                
                # Try to parse as form data (URL-encoded)
                if text_body and not json_body:
                    try:
                        from urllib.parse import parse_qs, unquote_plus
                        content_type_header = request.headers.get('content-type', '').lower()
                        
                        if 'application/x-www-form-urlencoded' in content_type_header or '=' in text_body:
                            print("[TRANSCRIPT] Attempting form data parsing...")
                            parsed_form = parse_qs(text_body, keep_blank_values=True)
                            print("[TRANSCRIPT] PARSED FORM DATA:")
                            for key, values in parsed_form.items():
                                decoded_key = unquote_plus(key)
                                decoded_values = [unquote_plus(v) for v in values]
                                print(f"  {decoded_key}: {decoded_values}")
                            form_data = parsed_form
                        
                        # Also try multipart form data indicators
                        elif 'multipart/form-data' in content_type_header:
                            print("[TRANSCRIPT] Multipart form data detected (raw content shown above)")
                            
                    except Exception as form_error:
                        print(f"[TRANSCRIPT] Form parsing error: {form_error}")
                        
            except UnicodeDecodeError:
                print(f"  Binary Content (hex): {raw_body.hex()}")
                print(f"  Binary Content (first 200 bytes): {raw_body[:200]}")
        else:
            print("  Empty body")
        
        print("=" * 60)
        
        # Process the transcript data if it's valid JSON
        processed_data = None
        if json_body:
            processed_data = await process_transcript_data(json_body)
            print("[TRANSCRIPT] PROCESSED DATA:")
            print(json.dumps(processed_data, indent=2, ensure_ascii=False))

        # Return success response
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Transcript received and processed successfully",
                "timestamp": datetime.now().isoformat(),
                "received_data": {
                    "has_json": json_body is not None,
                    "has_form": form_data is not None,
                    "headers_count": len(request.headers),
                    "query_params_count": len(request.query_params)
                },
                "processed_data": processed_data
            }
        )
        
    except Exception as e:
        print(f"[TRANSCRIPT] ERROR: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/transcript")
async def transcript_info():
    """
    GET endpoint to provide information about the transcript endpoint.
    """
    return {
        "endpoint": "/transcript",
        "method": "POST",
        "description": "Receives transcript data after voice bot call completion",
        "status": "listening",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/after-call")
async def after_call_webhook(request: Request):
    """
    Alternative endpoint for after call data.
    Some voice bot services might use different endpoint names.
    """
    try:
        print("=" * 60)
        print(f"[AFTER-CALL] Received at: {datetime.now()}")
        print(f"[AFTER-CALL] Method: {request.method}")
        print(f"[AFTER-CALL] URL: {request.url}")
        print("=" * 60)
        
        # Log all data similar to transcript endpoint
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        
        print("[AFTER-CALL] HEADERS:")
        content_type = ""
        for k, v in headers.items():
            print(f"  {k}: {v}")
            if k.lower() == 'content-type':
                content_type = v.lower()
        print(f"[AFTER-CALL] DETECTED CONTENT-TYPE: {content_type}")
        
        print("[AFTER-CALL] QUERY PARAMS:")
        for k, v in query_params.items():
            print(f"  {k}: {v}")
        
        # Get raw body first (can only be read once)
        raw_body = await request.body()
        print(f"[AFTER-CALL] RAW BODY ({len(raw_body)} bytes):")
        
        if len(raw_body) > 0:
            try:
                # Try to decode as text
                text_content = raw_body.decode('utf-8')
                print(f"[AFTER-CALL] TEXT CONTENT: {text_content}")
                
                # Try to parse as JSON
                try:
                    json_data = json.loads(text_content)
                    print("[AFTER-CALL] PARSED JSON:")
                    print(json.dumps(json_data, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print("[AFTER-CALL] Not JSON format")
                    
                    # Try form data parsing
                    try:
                        from urllib.parse import parse_qs, unquote_plus
                        
                        if 'application/x-www-form-urlencoded' in content_type or '=' in text_content:
                            parsed_form = parse_qs(text_content, keep_blank_values=True)
                            print("[AFTER-CALL] PARSED FORM DATA:")
                            for key, values in parsed_form.items():
                                decoded_key = unquote_plus(key)
                                decoded_values = [unquote_plus(v) for v in values]
                                print(f"  {decoded_key}: {decoded_values}")
                        elif 'multipart/form-data' in content_type:
                            print("[AFTER-CALL] Multipart form data detected")
                            
                    except Exception as form_error:
                        print(f"[AFTER-CALL] Form parsing error: {form_error}")
                        
            except UnicodeDecodeError:
                print(f"[AFTER-CALL] BINARY CONTENT (hex): {raw_body.hex()}")
        else:
            print("[AFTER-CALL] Empty body")
        
        print("=" * 60)
        
        # Process transcript data if JSON was successfully parsed
        processed_data = None
        if 'json_data' in locals() and json_data:
            processed_data = await process_transcript_data(json_data)
            print("[AFTER-CALL] PROCESSED DATA:")
            print(json.dumps(processed_data, indent=2, ensure_ascii=False))
        
        return {
            "status": "success",
            "message": "After call data received and processed",
            "timestamp": datetime.now().isoformat(),
            "processed_data": processed_data
        }
        
    except Exception as e:
        print(f"[AFTER-CALL] ERROR: {str(e)}")
        return {
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/transcript/test")
async def test_transcript_processing(request: Request):
    """
    Test endpoint to process sample transcript data.
    """
    try:
        # Enhanced sample data based on actual IVR format
        sample_data = {
            "dialer_id": "0",
            "did_no": "+918044475773",
            "client_no": "416102",
            "ext_no": "416102", 
            "customer_attended": "1",
            "call_time": "2025-10-10T20:00:52+05:30",
            "secret_key": "Voicebot",
            "call_conversation": [
                {"role": "user", "content": "नमस्ते"},
                {"role": "assistant", "content": "नमस्ते! मैं आपका कृषि सहायक वॉइस-बॉट हूँ। आप अपनी फसल की समस्या बता सकते हैं।"},
                {"role": "user", "content": "मैंने अपने पांच एकड़ में लगाई है मिर्ची और अभी इसमें मकड़ी की दिक्कत है"},
                {"role": "assistant", "content": "आपकी मिर्ची की फसल का क्षेत्रफल और मकड़ी की समस्या के बारे में बताएं। क्या आप मकड़ी के जाले देख रहे हैं?"},
                {"role": "user", "content": "हाँ, पत्तियों पर जाले हैं और पत्तियां सिकुड़ रही हैं। बहुत दिनों से आ रही है यह समस्या।"},
                {"role": "assistant", "content": "यह स्पाइडर माइट्स का संक्रमण है। क्या आपने हाल ही में कोई दवा का छिड़काव किया है?"},
                {"role": "user", "content": "हमने Abamectin डाला था तीन-चार दिन पहले पानी के साथ, लेकिन कोई फायदा नहीं हुआ।"},
                {"role": "assistant", "content": "Abamectin के अलावा आप नीम तेल का उपयोग कर सकते हैं। 15ml प्रति लीटर पानी में मिलाकर छिड़काव करें।"},
                {"role": "user", "content": "और कोई chemical दवा बताएं जो जल्दी काम करे।"},
                {"role": "assistant", "content": "आप Spiromesifen या Propargite का उपयोग कर सकते हैं। Spiromesifen 1ml/लीटर और Propargite 2ml/लीटर की दर से छिड़काव करें।"}
            ],
            "recording_url": "https://calls2.ivrsolutions.in/monitor/test.wav",
            "call_duration": "180",
            "outgoing_ext": "7000862419",
            "attended_by": "7000862419", 
            "recordid": "48350",
            "call_type": "outgoing"
        }
        
        # Get actual data from request if provided
        try:
            actual_data = await request.json()
            if actual_data:
                sample_data = actual_data
        except:
            pass  # Use sample data
        
        # Process the transcript
        processed_result = await process_transcript_data(sample_data)
        
        return {
            "status": "success",
            "message": "Test transcript processed successfully",
            "original_data": sample_data,
            "processed_result": processed_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e), 
            "timestamp": datetime.now().isoformat()
        }


@router.get("/transcript/format")
async def get_expected_format():
    """
    Get information about the expected transcript format.
    """
    return {
        "expected_format": {
            "dialer_id": "string - Dialer identifier",
            "did_no": "string - Customer phone number (e.g., +918044475773)",
            "client_no": "string - Client identifier", 
            "customer_attended": "string - '1' if attended, '0' if not",
            "call_time": "string - ISO timestamp (e.g., 2025-10-10T20:00:52+05:30)",
            "call_conversation": "array - Array of {role: 'user'|'assistant', content: 'text'}",
            "recording_url": "string - URL to call recording",
            "call_duration": "string - Duration in seconds",
            "recordid": "string - Unique record identifier",
            "call_type": "string - 'outgoing' or 'incoming'"
        },
        "processing_features": [
            "🤖 Advanced AI conversation analysis using ChatGPT-4o",
            "📊 Extracts key problems and farmer concerns from voice chat",
            "🌿 Generates specific organic solutions with exact ratios",
            "🧪 Provides Indian brand names and precise chemical dosages", 
            "💊 Creates shopping list with prices and where to buy",
            "📅 Develops 7-day treatment schedule with daily tasks",
            "⚠️ Includes safety warnings and application precautions",
            "📱 Sends screenshot-friendly comprehensive WhatsApp summary",
            "🔄 Enables progress tracking and follow-up support",
            "💾 Saves conversation analysis and solutions to database",
            "� Provides 24x7 support contact for emergencies"
        ],
        "endpoints": {
            "/transcript": "POST - Main endpoint for IVR webhook",
            "/after-call": "POST - Alternative endpoint",
            "/transcript/test": "POST - Test processing with sample/custom data",
            "/transcript/format": "GET - This documentation endpoint"
        }
    }
