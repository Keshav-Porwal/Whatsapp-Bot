from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.mongo_db import save_message
from app.services.gemini_api import get_treatment_followup, get_user_session_info
from app.services.follow_up_handler import follow_up_handler
from app.models import TreatmentRequest

router = APIRouter()

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


# New models for follow-up requests
class FollowUpRequest(BaseModel):
    user_id: str
    intent: str  # "treatment", "prevention", "medicine"
    crop_type: str = ""
    disease: str = ""


@router.post("/follow-up")
async def handle_follow_up_request(req: FollowUpRequest):
    """
    Handle follow-up requests for treatment, prevention, or medicine information.
    """
    try:
        # Validate intent
        valid_intents = ["treatment", "prevention", "medicine", "dosage", "cost", "management", "timing", "emergency"]
        if req.intent not in valid_intents:
            raise HTTPException(status_code=400, detail=f"Invalid intent. Must be one of: {valid_intents}")
        
        # If crop_type or disease not provided, try to get from recent conversation
        if not req.crop_type or not req.disease:
            analysis_info = follow_up_handler.get_last_analysis_info(req.user_id)
            crop_type = req.crop_type or analysis_info.get("crop_type", "")
            disease = req.disease or analysis_info.get("disease", "")
        else:
            crop_type = req.crop_type
            disease = req.disease
        
        # Generate response using follow-up handler
        response = follow_up_handler.generate_response(
            intent=req.intent,
            crop_type=crop_type,
            disease=disease,
            user_id=req.user_id
        )
        
        # Save interaction to database
        save_message(
            user_id=req.user_id,
            message=f"Follow-up request: {req.intent} for {crop_type}",
            is_bot=False,
            crop_type=crop_type
        )
        save_message(
            user_id=req.user_id,
            message=response,
            is_bot=True,
            crop_type=crop_type
        )
        
        # Get session info
        session_info = get_user_session_info(req.user_id)
        
        return {
            "user_id": req.user_id,
            "intent": req.intent,
            "crop_type": crop_type,
            "disease": disease,
            "response": response,
            "session_info": {
                "message_count": session_info.get("message_count", 0) if session_info else 0,
                "time_remaining": session_info.get("time_remaining", 0) if session_info else 0
            }
        }
        
    except Exception as e:
        error_msg = f"Follow-up request error: {str(e)}"
        return {
            "user_id": req.user_id,
            "error": error_msg,
            "intent": req.intent
        }


@router.get("/follow-up/intents")
async def get_available_intents():
    """
    Get list of available follow-up intents and their keywords.
    """
    return {
        "intents": {
            "treatment": {
                "description": "Detailed treatment and cure information",
                "keywords": {
                    "english": ["treatment", "detailed solution", "treat", "cure", "remedy", "fix", "heal", "solution"],
                    "hindi": ["उपचार", "इलाज", "समाधान", "चिकित्सा", "उपाय"]
                }
            },
            "prevention": {
                "description": "Prevention and future care guidelines", 
                "keywords": {
                    "english": ["prevention", "protection", "prevent", "avoid", "stop", "protect", "precaution", "safety"],
                    "hindi": ["रोकथाम", "बचाव", "सुरक्षा", "बचना", "रोकना", "सावधानी"]
                }
            },
            "medicine": {
                "description": "Medicine application and dosage guide",
                "keywords": {
                    "english": ["medicine", "pesticide", "medication", "drug", "spray", "fungicide", "chemical", "insecticide"],
                    "hindi": ["दवा", "कीटनाशक", "दवाई", "छिड़काव", "रसायन", "केमिकल", "स्प्रे"]
                }
            },
            "dosage": {
                "description": "Dosage calculator and quantity information",
                "keywords": {
                    "english": ["dosage", "quantity", "amount", "dose", "measurement", "calculation"],
                    "hindi": ["खुराक", "मात्रा", "डोज", "नाप", "परिमाण"]
                }
            },
            "cost": {
                "description": "Cost and budget information",
                "keywords": {
                    "english": ["cost", "budget", "price", "expense", "money", "rate", "charges"],
                    "hindi": ["कीमत", "लागत", "खर्च", "दाम", "रेट", "पैसा"]
                }
            },
            "management": {
                "description": "Crop management and care guidelines",
                "keywords": {
                    "english": ["management", "care", "farming", "cultivation", "maintenance", "handling"],
                    "hindi": ["प्रबंधन", "देखभाल", "खेती", "रखरखाव", "संभाल"]
                }
            },
            "timing": {
                "description": "Schedule and timing information",
                "keywords": {
                    "english": ["timing", "calendar", "schedule", "time", "when", "period", "duration"],
                    "hindi": ["समय", "कैलेंडर", "टाइमिंग", "कब", "अवधि", "समयसारणी"]
                }
            },
            "emergency": {
                "description": "Emergency help and urgent assistance",
                "keywords": {
                    "english": ["urgent", "emergency", "immediate", "asap", "critical", "serious", "help"],
                    "hindi": ["तुरंत", "आपातकाल", "जरूरी", "गंभीर", "मदद", "इमरजेंसी"]
                }
            }
        },
        "usage": "Send any of the keywords via WhatsApp after receiving crop analysis results"
    }


@router.post("/follow-up/test")
async def test_follow_up_detection(user_id: str, message: str):
    """
    Test endpoint to check follow-up detection and response generation.
    """
    try:
        # Test detection
        should_handle, detected_intent = follow_up_handler.should_handle_message(user_id, message)
        
        if not should_handle:
            return {
                "user_id": user_id,
                "message": message,
                "should_handle": False,
                "reason": "No follow-up context found or no intent detected"
            }
        
        # Get analysis context
        analysis_info = follow_up_handler.get_last_analysis_info(user_id)
        
        # Generate response
        if detected_intent:
            response = follow_up_handler.generate_response(
                intent=detected_intent,
                crop_type=analysis_info.get("crop_type", ""),
                disease=analysis_info.get("disease", ""),
                user_id=user_id
            )
        else:
            response = "No intent detected"
        
        return {
            "user_id": user_id,
            "message": message,
            "should_handle": True,
            "detected_intent": detected_intent,
            "analysis_info": analysis_info,
            "response": response
        }
        
    except Exception as e:
        return {
            "user_id": user_id,
            "error": str(e)
        }