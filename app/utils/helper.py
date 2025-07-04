from app.config import settings
import requests
import re
from app.config import settings

TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN

# Helper functions
def extract_phone_number(from_field: str) -> str:
    """Extract clean phone number from WhatsApp format"""
    # Remove 'whatsapp:' prefix if present
    phone = from_field.replace('whatsapp:', '').strip()
    return phone

def is_hindi_english_mixed(text: str) -> bool:
    """Check if text contains Hindi characters"""
    hindi_pattern = re.compile(r'[\u0900-\u097F]')
    return bool(hindi_pattern.search(text))



def format_whatsapp_message(message: str, max_length: int = 1500) -> list:
    """Smart message formatting for WhatsApp with Twilio limits"""
    # Twilio's actual limit is 1600 characters, but we use 1500 for safety
    if len(message) <= max_length:
        return [message]
    
    chunks = []
    
    # First try to split by double newlines (paragraphs/sections)
    sections = message.split('\n\n')
    current_chunk = ""
    
    for section in sections:
        # If adding this section exceeds limit
        if len(current_chunk + '\n\n' + section) > max_length:
            # Save current chunk if it has content
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If section itself is too long, split it further
            if len(section) > max_length:
                # Split by single newlines
                lines = section.split('\n')
                temp_chunk = ""
                for line in lines:
                    if len(temp_chunk + '\n' + line) > max_length:
                        if temp_chunk.strip():
                            chunks.append(temp_chunk.strip())
                        temp_chunk = line
                    else:
                        temp_chunk += '\n' + line if temp_chunk else line
                
                if temp_chunk.strip():
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = section
        else:
            current_chunk += '\n\n' + section if current_chunk else section
    
    # Add any remaining content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Final check - if any chunk is still too long, split by sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
        else:
            # Split by sentences (. or ! or ?)
            sentences = []
            temp_sentences = chunk.replace('!', '.').replace('?', '.').split('.')
            for sent in temp_sentences:
                if sent.strip():
                    sentences.append(sent.strip() + '.')
            
            temp_chunk = ""
            for sentence in sentences:
                if len(temp_chunk + ' ' + sentence) > max_length:
                    if temp_chunk.strip():
                        final_chunks.append(temp_chunk.strip())
                    temp_chunk = sentence
                else:
                    temp_chunk += ' ' + sentence if temp_chunk else sentence
            
            if temp_chunk.strip():
                final_chunks.append(temp_chunk.strip())
    
    return final_chunks if final_chunks else [message[:max_length]]



def download_twilio_media(media_url: str) -> bytes:
    """Download media from Twilio with proper authentication"""
    try:
        # Debug: Check if credentials are loaded
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise ValueError(f"Missing credentials: SID={'Present' if TWILIO_ACCOUNT_SID else 'Missing'}, Token={'Present' if TWILIO_AUTH_TOKEN else 'Missing'}")
        
        print(f"[DEBUG] Using Account SID: {TWILIO_ACCOUNT_SID[:8]}...")
        print(f"[DEBUG] Token length: {len(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else 0}")
        print(f"[DEBUG] Media URL: {media_url}")
        
        # Validate that SID starts with 'AC' (Twilio Account SID format)
        if not TWILIO_ACCOUNT_SID.startswith('AC'):
            raise ValueError(f"Invalid Account SID format. Should start with 'AC', got: {TWILIO_ACCOUNT_SID[:5]}...")
        
        # Method 1: Basic authentication with requests.auth
        response = requests.get(
            media_url,
            auth=(str(TWILIO_ACCOUNT_SID), str(TWILIO_AUTH_TOKEN)),
            timeout=30,
            headers={
                'User-Agent': 'TwilioMediaDownloader/1.0',
                'Accept': 'image/*'
            }
        )
        
        print(f"[DEBUG] Response status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"[DEBUG] Successfully downloaded {len(response.content)} bytes")
            return response.content
        
        # If 401, the credentials are definitely wrong
        if response.status_code == 401:
            print(f"[DEBUG] Authentication failed. Response: {response.text[:500]}")
            raise ValueError(f"Twilio authentication failed. Check your ACCOUNT_SID and AUTH_TOKEN. SID: {TWILIO_ACCOUNT_SID[:8]}...")
            
        # For other status codes, try alternative method
        print(f"[DEBUG] First method failed with status {response.status_code}, trying alternative...")
        
        # Method 2: Manual Authorization header
        import base64
        credentials = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
        
        response = requests.get(
            media_url,
            headers={
                'Authorization': f'Basic {credentials}',
                'User-Agent': 'TwilioMediaDownloader/1.0',
                'Accept': 'image/*'
            },
            timeout=30
        )
        
        print(f"[DEBUG] Alternative method status: {response.status_code}")
        
        if response.status_code == 200:
            return response.content
            
        # If still failing, provide detailed error
        raise ValueError(f"Failed to download image. Status: {response.status_code}, Response: {response.text[:300]}")
        
    except requests.exceptions.Timeout:
        raise ValueError("Image download timed out after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        raise ValueError(f"Connection error while downloading image: {str(e)}")
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        raise ValueError(f"Unexpected error during image download: {str(e)}")