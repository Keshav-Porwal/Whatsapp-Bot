from pydantic_settings import BaseSettings
from typing import Optional, List

class Settings(BaseSettings):
    # OpenAI & Gemini Configuration
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str = "https://agrostandai-openai-instance.openai.azure.com/"
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str  # WhatsApp number (e.g., 'whatsapp:+14155238886')
    
    # MongoDB Configuration
    MONGO_URI: str
    DATABASE_NAME: str = "crop_disease_bot"
    
    # Bot Configuration
    MAX_MESSAGE_LENGTH: int = 1500
    MAX_CONVERSATION_HISTORY: int = 10
    DEFAULT_TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 1200
    
    # Indian Agriculture Specific Settings
    SUPPORTED_LANGUAGES: List[str] = ["hindi", "english", "hinglish"]
    DEFAULT_LOCATION: str = "India"
    SUPPORTED_CROPS: List[str] = [
        "rice", "wheat", "cotton", "sugarcane", "maize", "pulses", 
        "soybean", "groundnut", "sunflower", "mustard", "potato",
        "tomato", "onion", "chili", "turmeric", "ginger"
    ]
    
    # AI Model Settings
    IMAGE_ANALYSIS_TEMPERATURE: float = 0.2
    TEXT_CHAT_TEMPERATURE: float = 0.35
    CONFIDENCE_THRESHOLD: float = 0.7
    
    # Rate Limiting
    REQUESTS_PER_MINUTE: int = 60
    REQUESTS_PER_HOUR: int = 1000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
