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
def analyze_crop_image(
    base64_image: str,
    prompt: str = """
    You are an agricultural expert specializing in Indian crops. A farmer from the Indian subcontinent has shared this image of a crop possibly suffering from a disease.

    1. Identify the most likely crop disease visible in the image. Mention the crop name if it’s clear.
    2. Provide possible root causes relevant to Indian agricultural conditions (e.g., monsoon impact, local pests, common fungal/bacterial issues in India).
    3. Suggest practical and affordable preventive or treatment measures suitable for Indian farmers.
    
    Keep the language simple and easy for a rural farmer to understand. Assume this is their primary source of livelihood.
    """
) -> str:

    model = genai.GenerativeModel("gemini-1.5-flash")

    # Decode and load image
    image_bytes = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_bytes))

    # Run Gemini with the regional context prompt
    response = model.generate_content([prompt.strip(), image])

    return response.text





# def analyze_crop_image(base64_image: str, prompt: str = "What crop disease is visible in this image?") -> str:
#     model = genai.GenerativeModel("gemini-1.5-flash")
    
#     # Decode the base64 image
#     image_bytes = base64.b64decode(base64_image)
#     image = Image.open(io.BytesIO(image_bytes))

#     response = model.generate_content([prompt, image])
#     return response.text
