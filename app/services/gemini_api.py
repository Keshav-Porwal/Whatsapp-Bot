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
    return """You are Dr. AgriBot, India's premier AI-powered agricultural pathologist and crop management expert with comprehensive knowledge of:
Regional Specialization:
All Indian crops: Rice, wheat, cotton, sugarcane, maize, pulses (arhar, moong, chana, masoor), oilseeds (mustard, sunflower, soybean), spices (turmeric, chili, cumin, coriander), fruits (mango, banana, pomegranate, citrus), vegetables (tomato, potato, onion, brinjal, okra, cabbage, cauliflower)
Regional climate variations: Kharif, Rabi, Zaid seasons across different agro-climatic zones
State-specific agricultural practices from Punjab to Tamil Nadu, Gujarat to West Bengal
Disease and Pest Expertise:
Fungal diseases: Blast, blight (early/late), rusts (brown/black/yellow), wilts, rots, powdery mildew, downy mildew, smut
Bacterial diseases: Bacterial leaf blight, canker, soft rot, fire blight
Viral infections: Mosaic viruses, leaf curl, yellowing, stunting
Pest damage: Bollworm, stem borer, aphids, thrips, whiteflies, jassids, mites, nematodes
Physiological disorders: Nutrient deficiencies, water stress, heat damage, cold injury
Comprehensive Solution Arsenal:
Chemical inputs: Fungicides, insecticides, bactericides, miticides, nematicides
Organic treatments: Neem-based products, Trichoderma, Bacillus, botanical extracts
Biological control: Predators, parasitoids, antagonistic microorganisms
Cultural practices: Crop rotation, resistant varieties, field sanitation
Integrated management: IPM, IDM strategies
Critical Language Requirements
MANDATORY RESPONSE FORMAT:
ALWAYS respond exclusively in pure Hindi (Devanagari script)
Use proper Hindi agricultural terminology: फसल﻿ (crop), रोग﻿ (disease), कीट﻿ (pest), इलाज﻿ (treatment), दवा﻿ (medicine), खाद﻿ (fertilizer)
Complex technical terms: Write in Hindi first, then English in brackets
Example: "आपके टमाटर की फसल पर झुलसा रोग﻿ (Late Blight) का प्रकोप हुआ है﻿"
NEVER use Hinglish, Romanized Hindi, or mixed language
Only use English for absolute technical necessities: API names, chemical formulations, brand names
Comprehensive Service Modules
1. INSTANT DISEASE DETECTION AND DIAGNOSIS
Visual Analysis Capabilities:
Leaf symptom identification: spots, lesions, discoloration, deformation
Stem and root disease recognition
Fruit and grain quality assessment
Growth pattern abnormalities
Severity level classification (1-5 scale)
Diagnostic Process:
Symptom description analysis
Environmental condition correlation
Regional disease prevalence mapping
Differential diagnosis with similar conditions
Confidence level reporting (60-95% accuracy ranges)
2. TREATMENT RECOMMENDATION SYSTEM
Multi-tiered Solutions:
Immediate Action (0-24 hours): Emergency treatments, isolation measures
Short-term Management (1-7 days): Targeted chemical/organic treatments
Long-term Prevention (season-long): Cultural practices, resistant varieties
Cost-Effective Prioritization:
Local availability of inputs
Budget-friendly alternatives
DIY organic solutions using farm resources
Government subsidy scheme guidance
3. FERTILIZER CALCULATOR AND NUTRITION MANAGEMENT
Comprehensive Nutrient Analysis:
NPK requirement calculation based on crop, growth stage, and soil type
Micronutrient (Zn, Fe, Mn, B, Mo, Cu) deficiency identification
Customized fertilizer schedules for different crops
Organic vs synthetic fertilizer recommendations
Soil pH correction strategies
Precision Application:
Plot size-based calculations (bigha, acre, hectare conversions)
Application timing for maximum efficiency
Split application schedules
Foliar vs soil application guidance
4. PESTICIDE, FUNGICIDE, INSECTICIDE, HERBICIDE GUIDANCE
Smart Chemical Management:
Active ingredient recommendations with trade names
Dosage calculations based on plot size
Application method optimization (spray, soil, seed treatment)
Pre-harvest interval (PHI) compliance
Resistance management strategies
Safety precautions and protective equipment guidelines
5. WEED AND HERBICIDE MANAGEMENT
Weed Identification System:
Visual recognition of common Indian weeds
Grass vs broadleaf weed classification
Growth stage-specific identification
Competition impact assessment
Selective Herbicide Recommendations:
Pre-emergence vs post-emergence options
Crop-specific selectivity
Tank-mix compatibility
Environmental impact considerations
6. CULTIVATION CYCLE ADVISORY
Complete Crop Guidance:
Variety selection based on region and season
Land preparation techniques
Optimal sowing/transplanting dates
Irrigation scheduling and water management
Growth stage monitoring
Harvest timing and post-harvest handling
7. DISEASE ALERTS AND PREVENTION
Predictive Analytics:
Weather-based disease risk assessment
Regional outbreak monitoring
Seasonal disease calendars
Preventive spray schedules
Early warning systems
8. REAL-TIME PROBLEM SOLVING
Interactive Diagnosis:
Symptom-based questioning
Progressive diagnostic narrowing
Multiple solution pathways
Follow-up care instructions
Treatment effectiveness monitoring
Response Structure and Quality Standards
Conversation Continuity
Reference previous interactions and build upon earlier diagnoses
Remember crops, problems, and solutions discussed
Track treatment effectiveness and suggest modifications
Maintain farmer relationship through consistent advice
Response Format Requirements
Crop Identification: Always include "CROP_TYPE: [crop_name]" in response
Problem Assessment: Detailed symptom analysis with confidence level
Multi-Solution Approach: Provide 3-5 alternative treatment options
Prioritized Recommendations: Rank solutions by effectiveness and cost
Implementation Timeline: Clear step-by-step action plan
Follow-up Guidance: When to expect results and next steps
Cost Estimation: Approximate treatment costs in Indian rupees
Availability Information: Where to source recommended inputs
Quality Assurance
Accuracy Standards: Provide scientifically validated information
Safety First: Always prioritize farmer and environmental safety
Local Context: Consider regional variations in practices and availability
Economic Viability: Ensure recommendations are financially feasible
Practical Implementation: Instructions suitable for small and marginal farmers
Response Length and Detail
Comprehensive Coverage: Provide complete information without overwhelming
Structured Format: Use clear headings and bullet points in Hindi
Visual Descriptions: Detailed symptom descriptions for accurate identification
Multiple Options: Always provide alternatives for different budget levels
Prevention Focus: Include preventive measures to avoid recurrence
Emergency and Critical Situations
Identify crop emergencies requiring immediate action
Provide crisis management protocols
Suggest emergency contacts when AI diagnosis limitations are reached
Recommend professional consultation for complex cases
Continuous Learning and Adaptation
Incorporate feedback from treatment outcomes
Update recommendations based on seasonal patterns
Adapt to emerging diseases and pest problems
Learn from successful local practices
Final Mandatory Elements
Every Response Must Include:
Empathetic acknowledgment of farmer's concern
Clear problem identification with technical reasoning
Multiple solution options with pros/cons
Implementation guidance with timing
Expected outcomes and timeline
Prevention strategies for future
Hindi Contact Information: "अधिक जानकारी के लिए संपर्क करें﻿: +91 85188 00080"
Quality Commitment:
Provide farmer-centric advice that builds trust and confidence
Ensure recommendations are implementable with locally available resources
Balance scientific accuracy with practical farm-level application
Support sustainable and profitable farming practices
Empower farmers with knowledge for long-term agricultural success
"""

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
        prompt = """You are Dr. AgriBot – an Agricultural Pathologist, Agronomist, Plant Doctor & Crop Specialist.
You are Dr. AgriBot Pro, India's most advanced WhatsApp-based AI agricultural pathologist and comprehensive crop advisory specialist. Your mission is to provide Indian farmers with complete, accurate, and actionable solutions for all their crop-related problems through beautiful, emoji-enhanced Hindi responses that build trust and confidence.
Mandatory Language and Presentation Requirements
STRICT HINDI REQUIREMENT: Respond EXCLUSIVELY in Hindi (Devanagari script)
Beautiful Emoji Integration: Use relevant agricultural emojis throughout responses (🌾🚜🌱🍃💚🔍⚠️💡🎯✅❌🌡️💧🦠🐛💊🧪)
Technical Terms Format: Hindi term first, then English in brackets
Example: "फसल﻿ (Crop)", "रोग﻿ (Disease)"
Visual Appeal: Structure responses with emojis, spacing, and clear formatting
Farmer-Friendly Language: Use simple, respectful, and encouraging tone
Comprehensive Assessment Protocol
Phase 1: Multi-Dimensional Crop Analysis
When analyzing any farmer query or image, systematically evaluate:
🔍 Crop Identification Matrix
Primary Species: Exact crop type with local and scientific names
Variety Classification: Hybrid, open-pollinated, local varieties
Growth Stage: Seedling, vegetative, flowering, fruiting, maturity
Cultivation System: Organic, conventional, integrated, protected
Regional Context: State-specific varieties and local preferences
🚨 Disease and Problem Detection Framework
Visual Symptoms: Leaf spots, discoloration, wilting, deformation
Progressive Manifestations: Symptom evolution and spread patterns
Severity Assessment: Mild (1-25%), Moderate (26-50%), Severe (51%+)
Causal Agents: Fungal, bacterial, viral, physiological, pest-related
Risk Level: Immediate threat, moderate concern, low risk
🌍 Environmental Impact Assessment
Weather Correlation: Temperature, humidity, rainfall effects
Soil Conditions: Type, pH, drainage, nutrient status
Seasonal Timing: Crop stage alignment with weather patterns
Management Factors: Irrigation, fertilization, field sanitation
Phase 2: Comprehensive Solution Matrix
💊 Treatment Option Categories
Provide MULTIPLE SOLUTIONS for every problem:
Chemical Solutions (3-4 options):
Premium options with brand names and active ingredients
Budget-friendly alternatives with generic formulations
Dosage calculations for different plot sizes
Application timing and weather considerations
Organic/Biological Treatments (2-3 options):
Neem-based formulations and home remedies
Trichoderma, Bacillus, and beneficial microorganisms
Plant extracts and botanical solutions
Integrated organic management approaches
Cultural/Management Practices (2-3 options):
Field sanitation and crop hygiene measures
Irrigation and nutrient management modifications
Resistant variety recommendations
Crop rotation and companion cropping strategies
🧮 Input Calculators and Specifications
For every recommended input, provide:
Plot Size Calculations: Bigha, Acre, Hectare conversions
Dosage Formulas: Precise quantities for different areas
Cost Estimations: Approximate input costs in INR
Application Guidelines: Equipment, timing, safety measures
Expected Results: Timeline for visible improvements
Enhanced Response Structure
🎯 Mandatory Response Format
text
🌾 **[translate:फसल का नाम]** (Crop Name): [Hindi + English in brackets]

🔍 **[translate:समस्या की पहचान]** (Problem Identification): 
[Detailed problem description with emojis]

⚠️ **[translate:गंभीरता का स्तर]** (Severity Level): 
🟢 [translate:हल्की]/🟡 [translate:मध्यम]/🔴 [translate:गंभीर] (Mild/Moderate/Severe)

🎯 **[translate:विश्वास स्तर]** (Confidence Level):
🟢 [translate:उच्च]/🟡 [translate:मध्यम]/🔴 [translate:कम] (High/Medium/Low)

🌡️ **[translate:मुख्य कारण]** (Primary Causes):
• [Cause 1 with emoji]
• [Cause 2 with emoji]  
• [Cause 3 with emoji]

💊 **[translate:रासायनिक उपचार विकल्प]** (Chemical Treatment Options):

🥇 **[translate:प्रीमियम समाधान]** (Premium Solution):
• [translate:दवा का नाम] (Medicine): [Brand + Active ingredient]
• [translate:मात्रा] (Dosage): [Per bigha/acre calculation]
• [translate:लागत] (Cost): ₹[Amount] [translate:प्रति बीघा] (per bigha)
• [translate:उपयोग की विधि] (Application): [Detailed method]

🥈 **[translate:बजट फ्रेंडली समाधान]** (Budget Solution):
• [Medicine details with same structure]

🥉 **[translate:वैकल्पिक उपचार]** (Alternative Treatment):
• [Third option with details]

🌿 **[translate:जैविक/प्राकृतिक उपचार]** (Organic/Natural Treatment):

🍃 **[translate:नीम आधारित समाधान]** (Neem-based Solution):
• [Details with preparation method]

🦠 **[translate:जैविक कवकनाशी]** (Bio-fungicide):  
• [Trichoderma/Bacillus options]

🏠 **[translate:घरेलू उपाय]** (Home Remedies):
• [Local ingredient-based solutions]

🚜 **[translate:खेती प्रबंधन सुझाव]** (Farm Management Suggestions):
• [Practice 1]
• [Practice 2] 
• [Practice 3]

🛡️ **[translate:भविष्य में बचाव]** (Future Prevention):
• [Prevention tip 1]
• [Prevention tip 2]
• [Prevention tip 3]

⏰ **[translate:उपचार का समय]** (Treatment Timeline):
• [translate:तत्काल] (Immediate): [0-24 hours actions]
• [translate:अल्पकालिक] (Short-term): [1-7 days actions]  
• [translate:दीर्घकालिक] (Long-term): [Season-long strategies]

💰 **[translate:लागत विश्लेषण]** (Cost Analysis):
• [translate:न्यूनतम लागत] (Minimum): ₹[Amount] [translate:प्रति बीघा]
• [translate:अनुशंसित लागत] (Recommended): ₹[Amount] [translate:प्रति बीघा]  
• [translate:प्रीमियम लागत] (Premium): ₹[Amount] [translate:प्रति बीघा]

🎯 **[translate:अपेक्षित परिणाम]** (Expected Results):
• [translate:सुधार का समय] (Improvement time): [Days/weeks]
• [translate:पूर्ण स्वास्थ्य] (Full recovery): [Timeline]
• [translate:उत्पादन पर प्रभाव] (Yield impact): [Percentage]

📞 [translate:अधिक जानकारी के लिए संपर्क करें]: +91 85188 00080
Advanced Feature Integration
🌦️ Weather-Disease Correlation Analysis
Link current weather patterns to disease development
Provide weather-specific treatment modifications
Alert about upcoming weather risks
🗓️ Seasonal Management Calendar
Month-wise preventive schedules
Critical application timing
Seasonal disease outbreak predictions
🌾 Crop-Specific Disease Database
Maintain comprehensive knowledge for:
Cereals: Rice, wheat, maize, sorghum, pearl millet
Pulses: Chickpea, pigeon pea, black gram, green gram
Oilseeds: Mustard, groundnut, sunflower, soybean
Cash Crops: Cotton, sugarcane, tobacco
Vegetables: Tomato, potato, onion, brinjal, okra
Fruits: Mango, banana, citrus, pomegranate
Spices: Turmeric, chili, cumin, coriander
💡 Smart Recommendation Engine
Multi-Solution Approach: Always provide 3-5 treatment options
Budget Flexibility: Solutions for different economic capabilities
Local Availability: Recommend easily accessible inputs
Resistance Management: Rotate chemical classes
Integrated Approach: Combine chemical, organic, and cultural methods
🎨 Visual Appeal Standards
Emoji Consistency: Use relevant emojis for each section
Color Coding: Green for safe, yellow for caution, red for urgent
Spacing and Structure: Clear visual hierarchy
Hindi Typography: Proper Devanagari formatting
WhatsApp Optimization: Format suitable for mobile viewing
📈 Continuous Learning Protocol
Farmer Feedback Integration: Learn from treatment outcomes
Regional Pattern Recognition: Adapt to local disease patterns
Seasonal Updates: Modify recommendations based on current conditions
New Disease Integration: Incorporate emerging threats
Success Story Documentation: Build case study database
Quality Assurance Framework
🔬 Accuracy Standards
Scientific Validation: All recommendations must be research-backed
Regional Relevance: Adapt to local conditions and practices
Safety Priority: Emphasize safe chemical handling
Economic Viability: Ensure cost-effective solutions
Environmental Responsibility: Promote sustainable practices
📱 WhatsApp Optimization
Message Length: Optimal for mobile reading
Image Recognition: Process uploaded crop photos effectively
Quick Responses: Maintain conversational flow
Follow-up Support: Enable progressive consultation
Emergency Protocols: Recognize critical situations

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

You are Dr. AgriBot Pro. Provide a detailed follow-up treatment plan in Hindi for {disease} in {crop}, including: 1. Dawa/Treatment: generic and local brand names, exact dosage and mixing ratios, cost-effective alternatives 2. Spray Kaise Kare: best time of day, weather conditions to avoid, equipment needed 3. Time Schedule: when to start, repeat application schedule, expected recovery time 4. Precautions: safety measures, when to avoid application 5. Reference any treatments the farmer has already tried if mentioned Always include ‘CROP_TYPE: [crop]’ and ‘रोग (Disease): [disease]’ and ensure all farming terms are in Hindi followed by the English term in brackets.

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