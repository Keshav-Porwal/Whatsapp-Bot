from app.services.session_manager import (
    add_user_message, 
    add_assistant_message,
    get_conversation_history,
    session_manager,
)

from typing import List, Tuple, Dict, Optional
from app.services.mongo_db import extract_crop_type_from_text

from openai import AzureOpenAI

# Import settings (assuming settings.py is in app/config or similar)
from app.config import settings  # Adjust the import path as needed

# Azure OpenAI client setup
client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint="https://agrostandai-openai-instance.openai.azure.com/",
    api_key=settings.OPENAI_API_KEY
)

def get_enhanced_system_prompt() -> str:
    """Returns the enhanced system prompt for crop disease identification"""
    return """You are Dr. AgriBot, an expert agricultural pathologist specializing in crop diseases of the Indian subcontinent. You have extensive knowledge of:

- Indian crops: Rice, wheat, cotton, sugarcane, pulses, oilseeds, spices, fruits, vegetables
- Regional diseases: Blast, blight, rust, wilt, rot, viral infections, pest damage
- Climate-specific issues: Monsoon diseases, heat stress, humidity-related problems
- Local farming practices and resource constraints

CONVERSATION CONTEXT:
- You can see the full conversation history with this user
- Reference previous messages when relevant
- Build upon earlier diagnoses and recommendations
- Remember crops and problems mentioned earlier

MANDATORY LANGUAGE REQUIREMENTS:
- ALWAYS respond in HINGLISH (Hindi-English mix)
- Use Hindi words for farming terms: fasal (crop), rog (disease), ilaj (treatment), dawa (medicine)
- Keep English for technical terms but explain in Hindi context
- Example: "Aapke tomato mein blight ka attack hai. Ye fungal infection hai jo moisture se hota hai."

IMPORTANT: When you identify a crop type, mention it clearly in your response using the format "CROP_TYPE: [crop_name]" somewhere in your response.

RESPONSE GUIDELINES:
1. Be PRECISE and ACTIONABLE - farmers need clear, implementable advice
2. Use Hinglish consistently - mix Hindi farming terms with English technical terms
3. Consider cost-effectiveness - suggest affordable treatments first
4. Mention timing - when to apply treatments, seasonal considerations
5. Provide confidence levels when uncertain
6. Suggest immediate vs. long-term actions
7. Keep responses concise for WhatsApp message limits
8. Reference earlier conversation when relevant

LANGUAGE STYLE:
- Professional but accessible Hinglish
- Empathetic to farmer's concerns
- Direct and solution-focused
- Use bullet points sparingly to keep messages short"""

def extract_crop_type_from_ai_response(response: str) -> str:
    """Extract crop type from AI response"""
    # Look for CROP_TYPE: pattern
    import re
    crop_match = re.search(r'CROP_TYPE:\s*([^\n]+)', response, re.IGNORECASE)
    if crop_match:
        return crop_match.group(1).strip()
    
    # Fallback to text extraction
    return extract_crop_type_from_text(response)

async def chat_with_gpt(message: str, user_id: str = "") -> Tuple[str, str]:
    """
    Enhanced text chat with session management - returns (response, crop_type)
    """
    try:
        # Add user message to session
        add_user_message(user_id, message)
        
        # Get conversation history with system prompt
        system_prompt = get_enhanced_system_prompt()
        conversation_history = get_conversation_history(user_id, system_prompt)
        
        print(f"[CHAT] User {user_id}: {len(conversation_history)} messages in context")
        
        # Type annotations for OpenAI messages
        from openai.types.chat import (
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
            ChatCompletionAssistantMessageParam,
        )
        
        # Convert conversation history to proper types
        typed_messages: List[
            ChatCompletionSystemMessageParam | 
            ChatCompletionUserMessageParam | 
            ChatCompletionAssistantMessageParam
        ] = []
        
        for msg in conversation_history:
            if msg["role"] == "system":
                typed_messages.append(ChatCompletionSystemMessageParam(
                    role="system",
                    content=msg["content"]
                ))
            elif msg["role"] == "user":
                if isinstance(msg["content"], str):
                    typed_messages.append(ChatCompletionUserMessageParam(
                        role="user",
                        content=msg["content"]
                    ))
                else:
                    # Handle image content
                    typed_messages.append(ChatCompletionUserMessageParam(
                        role="user",
                        content=msg["content"]
                    ))
            elif msg["role"] == "assistant":
                typed_messages.append(ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=msg["content"]
                ))

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=typed_messages,
            temperature=0.3,
            max_tokens=600,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        content = response.choices[0].message.content
        reply = content.strip() if content else ""
        
        # Add assistant response to session
        add_assistant_message(user_id, reply)
        
        # Extract crop type from AI response
        crop_type = extract_crop_type_from_ai_response(reply)
        
        # If no crop type found in AI response, try extracting from user message
        if not crop_type:
            crop_type = extract_crop_type_from_text(message)
        
        return reply, crop_type
        
    except Exception as e:
        error_msg = f"⚠️ Technical problem hai. Phir se try kariye. (Error: {str(e)})"
        # Add error message to session
        add_assistant_message(user_id, error_msg)
        return error_msg, ""

async def analyze_crop_image(
    base64_image: str,
    user_id: Optional[str] = None,
    prompt: Optional[str] = None
) -> Tuple[str, str]:
    """
    Enhanced image analysis with session management - returns (analysis_result, crop_type)
    """
    
    if not prompt:
        prompt = """You are Dr. AgriBot, an expert agricultural pathologist for Indian farmers.

CONVERSATION CONTEXT:
- You can see the full conversation history with this user
- Reference previous messages and images when relevant
- Build upon earlier diagnoses if this is a follow-up image
- Remember crops and problems mentioned earlier

MANDATORY: Respond ONLY in HINGLISH (Hindi-English mix). Use Hindi words for farming terms mixed with English technical terms.

IMPORTANT: When you identify a crop, mention it clearly using the format "CROP_TYPE: [crop_name]" somewhere in your response.

ANALYSIS PROTOCOL:
1. Crop Identification: Identify the crop species first  
2. Disease/Problem Detection: Look for visible symptoms:
   - Leaf spots, discoloration, wilting
   - Stem damage, root issues
   - Pest damage, fungal growth
   - Nutritional deficiencies  
3. Severity Assessment: Rate as Mild/Moderate/Severe  
4. Confidence Level: State your diagnostic confidence (High/Medium/Low)
5. Context Awareness: Reference previous conversation if relevant

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

IMPORTANT: Keep the total message under 800 characters for WhatsApp limits. Be concise but complete."""

    try:
        # Add image message to session
        if user_id:
            add_user_message(user_id, "[Image uploaded for analysis]", base64_image)
        
        # Get conversation history
        system_prompt = prompt
        if user_id:
            conversation_history = get_conversation_history(user_id, system_prompt)
            print(f"[IMAGE_ANALYSIS] User {user_id}: {len(conversation_history)} messages in context")
        else:
            conversation_history = [{"role": "system", "content": system_prompt}]
        
        from openai.types.chat import (
            ChatCompletionUserMessageParam,
            ChatCompletionContentPartTextParam,
            ChatCompletionContentPartImageParam,
        )

        # Prepare the current image analysis message using OpenAI SDK types
        text_part = ChatCompletionContentPartTextParam(
            type="text",
            text=prompt.strip()
        )
        image_part = ChatCompletionContentPartImageParam(
            type="image_url",
            image_url={
                "url": "data:image/jpeg;base64," + base64_image
            }
        )

        # If we have conversation history, use it; otherwise, create a simple message
        if len(conversation_history) > 1:  # More than just system message
            # Use conversation history but replace the last message with image analysis
            messages = []
            for msg in conversation_history[:-1]:
                if msg["role"] == "system":
                    messages.append({"role": "system", "content": msg["content"]})
                elif msg["role"] == "user":
                    messages.append({"role": "user", "content": msg["content"]})
                elif msg["role"] == "assistant":
                    messages.append({"role": "assistant", "content": msg["content"]})
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=[text_part, image_part]
                )
            )
        else:
            # Simple image analysis without context
            messages = [
                {"role": "system", "content": system_prompt},
                ChatCompletionUserMessageParam(
                    role="user",
                    content=[text_part, image_part]
                )
            ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        
        content = response.choices[0].message.content
        analysis_result = content.strip() if content else ""
        
        # Add analysis result to session
        if user_id:
            add_assistant_message(user_id, analysis_result)
        
        # Extract crop type from AI response
        crop_type = extract_crop_type_from_ai_response(analysis_result)
        
        return analysis_result, crop_type
        
    except Exception as e:
        error_msg = f"⚠️ Image analysis mein problem hai"
        if "rate limit" in str(e).lower():
            error_msg += "\n🕐 1 minute baad try kariye"
        elif "invalid image" in str(e).lower():
            error_msg += "\n📸 Clear photo bhejiye please"
        else:
            error_msg += f"\n🔧 Technical issue: {str(e)}"
        
        # Add error message to session
        if user_id:
            add_assistant_message(user_id, error_msg)
        
        return error_msg, ""

def get_treatment_followup(disease: str, crop: str, user_id: Optional[str] = None) -> str:
    """Provides detailed treatment follow-up for identified diseases with session context"""
    
    # Add treatment request to session
    if user_id:
        treatment_request = f"Tell me more about treatment for {disease} in {crop}"
        add_user_message(user_id, treatment_request)
    
    prompt = f"""Based on our conversation history, provide detailed treatment guidance for {disease} in {crop} for Indian farmers.

CONVERSATION CONTEXT:
- Reference our previous discussion about this crop/disease
- Build upon earlier recommendations
- Consider what the farmer has already tried (if mentioned)

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
        # Get conversation history if user_id provided
        if user_id:
            conversation_history = get_conversation_history(user_id, prompt)
        else:
            conversation_history = [{"role": "user", "content": prompt}]
        
        # Convert conversation_history to proper OpenAI message types
        from openai.types.chat import (
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
            ChatCompletionAssistantMessageParam,
        )
        typed_messages = []
        for msg in conversation_history:
            if msg["role"] == "system":
                typed_messages.append(ChatCompletionSystemMessageParam(
                    role="system",
                    content=msg["content"]
                ))
            elif msg["role"] == "user":
                typed_messages.append(ChatCompletionUserMessageParam(
                    role="user",
                    content=msg["content"]
                ))
            elif msg["role"] == "assistant":
                typed_messages.append(ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=msg["content"]
                ))

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=typed_messages,
            temperature=0.3,
            max_tokens=600
        )
        
        content = response.choices[0].message.content
        treatment_response = content.strip() if content else ""
        
        # Add treatment response to session
        if user_id:
            add_assistant_message(user_id, treatment_response)
        
        return treatment_response
        
    except Exception as e:
        error_msg = f"⚠️ Treatment info mein problem: {str(e)}"
        if user_id:
            add_assistant_message(user_id, error_msg)
        return error_msg

# Session management utility functions
def get_user_session_info(user_id: str) -> Optional[Dict]:
    """Get session information for a user"""
    return session_manager.get_session_info(user_id)

def clear_user_conversation(user_id: str) -> bool:
    """Clear user's conversation history"""
    return session_manager.clear_session(user_id)

def get_active_sessions_count() -> int:
    """Get count of active sessions"""
    return session_manager.get_active_sessions_count()

def get_all_sessions_info() -> Dict:
    """Get information about all active sessions"""
    return session_manager.get_all_sessions_info()