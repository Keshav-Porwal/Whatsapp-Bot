from pymongo import MongoClient
from app.config import settings
from app.utils.helper import extract_phone_number
from datetime import datetime
from app.models import MessageSchema, UserSchema

client = MongoClient(settings.MONGO_URI)
db = client["whatsapp_bot"]

# Collections
users_collection = db["users"]
# Ensure the "messages" collection exists or is referenced correctly
messages_collection = db.get_collection("messages")


def save_user(user_id: str, phone_number: str = "", name: str = ""):
    """Save user info only once - prevents duplicates"""
    # Clean phone number
    clean_phone = extract_phone_number(phone_number) if phone_number else ""
    
    # Check if user already exists
    existing_user = users_collection.find_one({"user_id": user_id})
    
    if not existing_user:
        user_data = UserSchema(
            user_id=user_id,
            phone_number=clean_phone,
            name=name if name else None
        ).dict()
        users_collection.insert_one(user_data)
        print(f"[DB] New user saved: {user_id} | Phone: {clean_phone}")
    else:
        # Update phone number if it wasn't stored before
        if clean_phone and not existing_user.get("phone_number"):
            users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "phone_number": clean_phone,
                        "updated_at": datetime.now()
                    }
                }
            )
            print(f"[DB] User phone updated: {user_id} | Phone: {clean_phone}")

def save_message(user_id: str, message: str = "", image_base64: str = "", 
                is_bot: bool = False, crop_type: str = ""):
    """Save message with all required fields"""
    
    # Get user's phone number
    user = users_collection.find_one({"user_id": user_id})
    phone_number = user.get("phone_number", "") if user else ""
    
    message_obj = MessageSchema(
        user_id=user_id,
        phone_number=phone_number,
        message=message,
        image_base64=image_base64,
        crop_type=crop_type,
        is_bot=is_bot
    )
    message_data = message_obj.dict()
    
    result = messages_collection.insert_one(message_data)
    print(f"[DB] Message saved: {user_id} | Bot: {is_bot} | Crop: {crop_type}")
    return result.inserted_id

def get_user_phone(user_id: str) -> str:
    """Get user's phone number"""
    user = users_collection.find_one({"user_id": user_id})
    return user.get("phone_number", "") if user else ""

def get_recent_messages(user_id: str, limit: int = 10):
    """Get recent messages for a user (for context if needed)"""
    messages = messages_collection.find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(limit)
    
    return list(messages)

def extract_crop_type_from_text(text: str) -> str:
    """Simple crop type extraction from text"""
    text_lower = text.lower()
    
    # Common crop keywords in Hindi and English
    crop_keywords = {
        'rice': ['rice', 'chawal', 'dhan', 'paddy'],
        'wheat': ['wheat', 'gehun', 'gahu'],
        'cotton': ['cotton', 'kapas', 'rui'],
        'tomato': ['tomato', 'tamatar'],
        'potato': ['potato', 'aloo', 'batata'],
        'onion': ['onion', 'pyaj', 'kanda'],
        'sugarcane': ['sugarcane', 'ganna', 'ikhu'],
        'maize': ['maize', 'corn', 'makka', 'bhutta'],
        'soybean': ['soybean', 'soya', 'bhatmas'],
        'groundnut': ['groundnut', 'peanut', 'moongfali'],
        'banana': ['banana', 'kela'],
        'mango': ['mango', 'aam'],
        'chili': ['chili', 'pepper', 'mirch', 'lal mirch'],
        'cabbage': ['cabbage', 'patta gobi'],
        'cauliflower': ['cauliflower', 'phool gobi'],
        'brinjal': ['brinjal', 'eggplant', 'baingan'],
        'okra': ['okra', 'bhindi', 'lady finger']
    }
    
    for crop, keywords in crop_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return crop
    
    return ""