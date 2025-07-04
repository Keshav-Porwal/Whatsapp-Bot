from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import Field

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

class MessageSchema(BaseModel):
    user_id: str
    phone_number: Optional[str] = ""
    message: Optional[str] = ""
    image_base64: Optional[str] = ""
    crop_type: Optional[str] = ""
    is_bot: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)

class UserSchema(BaseModel):
    user_id: str
    phone_number: Optional[str] = ""
    name: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
