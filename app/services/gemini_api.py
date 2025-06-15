from openai import AzureOpenAI
from app.config import settings
import base64
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.services.mongo_db import append_conversation_history, get_conversation_history
from app.services.mongo_db import get_user_context, update_user_context

# Azure OpenAI client setup
client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="https://agrostandai-openai-instance.openai.azure.com/",
    api_key=settings.OPENAI_API_KEY
)

class CropAnalysisContext:
    """Maintains conversation context for intelligent follow-up questions"""
    def __init__(self):
        self.user_sessions: Dict[str, Dict] = {}
    
    def get_user_context(self, user_id: str) -> Dict:
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "conversation_history": [],
                "identified_diseases": [],
                "crop_type": None,
                "location": None,
                "season": None,
                "last_analysis": None,
                "pending_questions": []
            }
        return self.user_sessions[user_id]
    
    def update_context(self, user_id: str, **kwargs):
        context = self.get_user_context(user_id)
        context.update(kwargs)

# Global context manager
context_manager = CropAnalysisContext()

def get_enhanced_system_prompt() -> str:
    """Returns the enhanced system prompt for crop disease identification"""
    return """You are Dr. AgriBot, an expert agricultural pathologist specializing in crop diseases of the Indian subcontinent. You have extensive knowledge of:

- Indian crops: Rice, wheat, cotton, sugarcane, pulses, oilseeds, spices, fruits, vegetables
- Regional diseases: Blast, blight, rust, wilt, rot, viral infections, pest damage
- Climate-specific issues: Monsoon diseases, heat stress, humidity-related problems
- Local farming practices and resource constraints

MANDATORY LANGUAGE REQUIREMENTS:
- ALWAYS respond in HINGLISH (Hindi-English mix)
- Use Hindi words for farming terms: fasal (crop), rog (disease), ilaj (treatment), dawa (medicine)
- Keep English for technical terms but explain in Hindi context
- Example: "Aapke tomato mein blight ka attack hai. Ye fungal infection hai jo moisture se hota hai."

RESPONSE GUIDELINES:
1. Be PRECISE and ACTIONABLE - farmers need clear, implementable advice
2. Use Hinglish consistently - mix Hindi farming terms with English technical terms
3. Consider cost-effectiveness - suggest affordable treatments first
4. Mention timing - when to apply treatments, seasonal considerations
5. Ask intelligent follow-up questions ONLY when necessary for better diagnosis
6. Provide confidence levels when uncertain
7. Suggest immediate vs. long-term actions
8. Keep responses concise for WhatsApp message limits

CONVERSATION INTELLIGENCE:
- If diagnosis is clear and complete, don't ask unnecessary questions
- If symptoms are ambiguous, ask 1-2 specific clarifying questions
- Always prioritize farmer's immediate needs over theoretical completeness
- End with clear next steps when diagnosis is confident

LANGUAGE STYLE:
- Professional but accessible Hinglish
- Empathetic to farmer's concerns
- Direct and solution-focused
- Use bullet points sparingly to keep messages short"""

def analyze_conversation_need(message: str, context: Dict) -> str:
    """Determines what type of response is needed based on context"""
    message_lower = message.lower()
    
    # Check if this is a greeting/introduction
    if any(word in message_lower for word in ['hello', 'hi', 'namaste', 'help', 'start']):
        return "greeting"
    
    # Check if asking about previous diagnosis
    if any(word in message_lower for word in ['treatment', 'medicine', 'spray', 'cure', 'how to']):
        if context.get('last_analysis'):
            return "follow_up_treatment"
    
    # Check if providing additional information
    if any(word in message_lower for word in ['location', 'state', 'weather', 'rain', 'temperature']):
        return "additional_info"
    
    # Check if asking about prevention
    if any(word in message_lower for word in ['prevent', 'avoid', 'stop', 'future']):
        return "prevention"
    
    return "general_query"

def chat_with_gpt(message: str, user_id: str = None) -> str:
    """Enhanced text chat with context awareness"""
    try:
        # Get user context if available
        context = get_user_context(user_id) if user_id else {}
        conversation_type = analyze_conversation_need(message, context)
        
        # Build context-aware prompt
        system_prompt = get_enhanced_system_prompt()
        
        # Add context information
        context_info = ""
        if context.get('crop_type'):
            context_info += f"Previously identified crop: {context['crop_type']}\n"
        if context.get('identified_diseases'):
            context_info += f"Previous diagnoses: {', '.join(context['identified_diseases'])}\n"
        if context.get('location'):
            context_info += f"Farmer location: {context['location']}\n"
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt + "\n" + context_info}
        ]
        
        # Add conversation history (last 3 exchanges to maintain context)
        if user_id:
            history = get_conversation_history(user_id, limit=6)
            for exchange in history:
                messages.append(exchange)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent medical advice
            max_tokens=600,  # Reduced for shorter WhatsApp messages
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        reply = response.choices[0].message.content.strip()
        
        # Update context
        if user_id:
            append_conversation_history(user_id, "user", message)
            append_conversation_history(user_id, "assistant", reply)
        
        return reply
        
    except Exception as e:
        return f"⚠️ Technical problem hai. Phir se try kariye. (Error: {str(e)})"

def analyze_crop_image(
    base64_image: str,
    user_id: str = None,
    prompt: str = None
) -> str:
    """Enhanced image analysis with intelligent questioning"""
    
    if not prompt:
        prompt = """You are Dr. AgriBot, an expert agricultural pathologist for Indian farmers.

MANDATORY: Respond ONLY in HINGLISH (Hindi-English mix). Use Hindi words for farming terms mixed with English technical terms.

ANALYSIS PROTOCOL:
1. Crop Identification: Identify the crop species first  
2. Disease/Problem Detection: Look for visible symptoms:
   - Leaf spots, discoloration, wilting
   - Stem damage, root issues
   - Pest damage, fungal growth
   - Nutritional deficiencies  
3. Severity Assessment: Rate as Mild/Moderate/Severe  
4. Confidence Level: State your diagnostic confidence (High/Medium/Low)  

RESPONSE FORMAT (HINGLISH ONLY):  
🌾 **Fasal**: [Crop name in Hinglish]  
🔍 **Problem**: [Disease/Issue in Hinglish]  
📊 **Severity**: [Mild/Moderate/Severe]  
🎯 **Confidence**: [High/Medium/Low]  

**Causes**  
- [Cause 1 in Hinglish]  
- [Cause 2 in Hinglish]  

**Turant Ilaj (Immediate Treatment)**  
- [Solution 1 in Hinglish]  
- [Solution 2 in Hinglish]  

**Prevention**  
- [Preventive tip 1]  
- [Preventive tip 2]  
- [Preventive tip 3]  

**Suggested Products (Links)**  
Based on the detected problem, suggest 3 useful products from the following companies only: [INSERT COMPANY NAMES HERE].  
Each product should include its name, purpose, and a clickable link in this format:  
🔗 Product Name – Short use – URL  

IMPORTANT: Keep the total message under 800 characters for WhatsApp limits. Be concise but complete.  

If confidence is Medium or Low, ask ONE specific follow-up question in Hinglish.  
If confidence is High, give full response with treatment and product suggestions without asking any question."""


    context = get_user_context(user_id) if user_id else {}
    
    # Add context to prompt if available
    if context.get('location'):
        prompt += f"\nFarmer's location: {context['location']} (consider regional disease patterns)"
    
    image_data = {
        "type": "image_url",
        "image_url": {
            "url": "data:image/jpeg;base64," + base64_image
        }
    }
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt.strip()},
                    image_data
                ]}
            ],
            temperature=0.2,  # Very low temperature for consistent medical diagnosis
            max_tokens=800  # Reduced for WhatsApp message limits
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        # Extract key information and update context
        if user_id:
            # Simple extraction logic - in production, you might want more sophisticated parsing
            context['last_analysis'] = {
                'timestamp': datetime.now().isoformat(),
                'result': analysis_result
            }
            
            # Try to extract crop type and disease
            lines = analysis_result.lower().split('\n')
            if 'identified_diseases' not in context or context['identified_diseases'] is None:
                context['identified_diseases'] = []
            for line in lines:
                if 'crop' in line or 'फसल' in line:
                    if ':' in line:
                        crop_info = line.split(':')[1].strip()
                        context['crop_type'] = crop_info
            if 'problem' in line or 'समस्या' in line:
                if ':' in line:
                    disease_info = line.split(':')[1].strip()
                    if disease_info not in context['identified_diseases']:
                        context['identified_diseases'].append(disease_info)
                            
            update_user_context(user_id, {
                "crop_type": context.get("crop_type"),
                "identified_diseases": context.get("identified_diseases"),
                "last_analysis": context.get("last_analysis"),
                "location": context.get("location")
            })
                            
        return analysis_result
        
    except Exception as e:
        error_msg = f"⚠️ Image analysis mein problem hai"
        if "rate limit" in str(e).lower():
            error_msg += "\n🕐 1 minute baad try kariye"
        elif "invalid image" in str(e).lower():
            error_msg += "\n📸 Clear photo bhejiye please"
        else:
            error_msg += f"\n🔧 Technical issue: {str(e)}"
        
        return error_msg

def get_treatment_followup(disease: str, crop: str, user_id: str = None) -> str:
    """Provides detailed treatment follow-up for identified diseases"""
    prompt = f"""Provide detailed treatment guidance for {disease} in {crop} for Indian farmers.

MANDATORY: Respond in HINGLISH only (Hindi-English mix).

Include:
1. **Dawa/Treatment**:
   - Generic aur local brand names
   - Exact dosage aur mixing ratios
   - Cost-effective alternatives

2. **Spray Kaise Kare**:
   - Best time of day (morning/evening)
   - Weather conditions to avoid
   - Equipment needed

3. **Time Schedule**:
   - Kab start karna hai
   - Repeat application schedule
   - Expected recovery time

4. **Precautions**:
   - Safety measures
   - Kab avoid karna hai

Keep it practical and affordable for small Indian farmers. Response should be under 1000 characters."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600  # Reduced for shorter messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Treatment info mein problem: {str(e)}"

# Legacy function names for backward compatibility
def chat_with_gemini(message: str, user_id: str = None) -> str:
    """Legacy function name - redirects to enhanced chat"""
    return chat_with_gpt(message, user_id)