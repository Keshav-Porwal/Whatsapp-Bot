import google.generativeai as genai
from app.config import settings
from PIL import Image
import io
import base64

genai.configure(api_key=settings.GEMINI_API_KEY)

# TEXT chat using gemini-pro
def chat_with_gemini(message: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(message)
    return response.text

# IMAGE analysis using gemini-pro-vision
def analyze_crop_image(base64_image: str, prompt: str = "What crop disease is visible in this image?") -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Decode the base64 image
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_bytes))

    response = model.generate_content([prompt, image])
    return response.text
