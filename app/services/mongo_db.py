from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)

db = client["whatsapp_bot"]  # database name

users_collection = db["users"]
messages_collection = db["messages"]

def save_user(user_id: str, name: str = ""):
    users_collection.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {"user_id": user_id, "name": name}},
        upsert=True
    )

def save_message(user_id: str, message: str, is_bot: bool):
    messages_collection.insert_one({
        "user_id": user_id,
        "message": message,
        "is_bot": is_bot
    })
