from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)

db = client["whatsapp_bot"]  # database name

users_collection = db["users"]
messages_collection = db["messages"]

def save_user(user_id: str, name: str = ""):
    users_collection.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"user_id": user_id, "name": name, "conversation_history": []}},
        upsert=True
    )

def save_message(user_id: str, message: str, is_bot: bool):
    messages_collection.insert_one({
        "user_id": user_id,
        "message": message,
        "is_bot": is_bot
    })
    
def append_conversation_history(user_id: str, role: str, content: str):
    users_collection.update_one(
        {"user_id": user_id},
        {"$push": {"conversation_history": {"role": role, "content": content}}},
        upsert=True
    )

def get_conversation_history(user_id: str, limit: int = 6):
    user = users_collection.find_one({"user_id": user_id})
    if user and "conversation_history" in user:
        # Return the last `limit` messages (3 Q&A pairs)
        return user["conversation_history"][-limit:]
    return []

def update_user_context(user_id: str, context: dict):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": context},
        upsert=True
    )

def get_user_context(user_id: str) -> dict:
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        # Return a default structure if user not found
        return {
            "conversation_history": [],
            "identified_diseases": [],
            "crop_type": None,
            "location": None,
            "last_analysis": None
        }
    return user
