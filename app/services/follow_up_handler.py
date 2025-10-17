"""
Follow-up Handler Service
Handles keyword detection and response generation for post-analysis follow-up messages.
"""

import re
from typing import Dict, List, Tuple, Optional
from app.services.mongo_db import get_recent_messages
from app.services.gemini_api import get_treatment_followup

class FollowUpHandler:
    """
    Handles detection and response for follow-up keywords after crop analysis.
    """
    
    def __init__(self):
        # Define keyword mappings for different intents (8 categories)
        self.intent_keywords = {
            "treatment": {
                "english": ["treatment", "detailed solution", "treat", "cure", "remedy", "fix", "heal", "solution"],
                "hindi": ["उपचार", "इलाज", "समाधान", "चिकित्सा", "उपाय"]
            },
            "prevention": {
                "english": ["prevention", "protection", "prevent", "avoid", "stop", "protect", "precaution", "safety"],
                "hindi": ["रोकथाम", "बचाव", "सुरक्षा", "बचना", "रोकना", "सावधानी"]
            },
            "medicine": {
                "english": ["medicine", "pesticide", "medication", "drug", "spray", "fungicide", "chemical", "insecticide"],
                "hindi": ["दवा", "कीटनाशक", "दवाई", "छिड़काव", "रसायन", "केमिकल", "स्प्रे"]
            },
            "dosage": {
                "english": ["dosage", "quantity", "amount", "dose", "measurement", "calculation"],
                "hindi": ["खुराक", "मात्रा", "डोज", "नाप", "परिमाण"]
            },
            "cost": {
                "english": ["cost", "budget", "price", "expense", "money", "rate", "charges"],
                "hindi": ["कीमत", "लागत", "खर्च", "दाम", "रेट", "पैसा"]
            },
            "management": {
                "english": ["management", "care", "farming", "cultivation", "maintenance", "handling"],
                "hindi": ["प्रबंधन", "देखभाल", "खेती", "रखरखाव", "संभाल"]
            },
            "timing": {
                "english": ["timing", "calendar", "schedule", "time", "when", "period", "duration"],
                "hindi": ["समय", "कैलेंडर", "टाइमिंग", "कब", "अवधि", "समयसारणी"]
            },
            "emergency": {
                "english": ["urgent", "emergency", "immediate", "asap", "critical", "serious", "help"],
                "hindi": ["तुरंत", "आपातकाल", "जरूरी", "गंभीर", "मदद", "इमरजेंसी"]
            }
        }
        
        # Define response templates for all 8 categories
        self.response_templates = {
            "treatment": {
                "intro": "💊 **विस्तृत उपचार गाइड (Detailed Treatment Guide):**\n",
                "detailed_request": True  # Will use Gemini API for detailed response
            },
            "prevention": {
                "intro": "🛡️ **भविष्य में बचाव (Future Prevention):**\n",
                "content": [
                    "🔍 **नियमित निगरानी (Regular Monitoring):**",
                    "• हर 7-10 दिन में खेत की जांच करें (Inspect field every 7-10 days)",
                    "• सुबह-शाम पत्तियों की जांच (Check leaves morning-evening)",
                    "",
                    "🌱 **फसल स्वास्थ्य (Crop Health):**",
                    "• पौधों के बीच उचित दूरी (Proper plant spacing)",
                    "• अच्छी जल निकासी व्यवस्था (Good drainage system)",
                    "• फसल चक्र अपनाएं (Practice crop rotation)",
                    "",
                    "🌿 **प्राकृतिक बचाव (Natural Protection):**",
                    "• रोग प्रतिरोधी किस्में उगाएं (Use resistant varieties)",
                    "• खेत की सफाई बनाए रखें (Maintain field hygiene)",
                    "• मौसम की निगरानी करें (Monitor weather conditions)"
                ]
            },
            "medicine": {
                "intro": "🧪 **दवा की पूरी जानकारी (Complete Medicine Information):**\n",
                "content": [
                    "⏰ **छिड़काव का समय (Application Time):**",
                    "• सुबह 6-8 बजे या शाम 4-6 बजे (6-8 AM or 4-6 PM)",
                    "• हवा कम हो और धूप तेज न हो (Low wind, mild sunlight)",
                    "",
                    "💧 **मिश्रण तैयार करना (Preparation):**",
                    "• साफ पानी का इस्तेमाल करें (Use clean water)",
                    "• पहले दवा, फिर पानी मिलाएं (Add chemical first, then water)",
                    "• तुरंत इस्तेमाल करें (Use immediately)",
                    "",
                    "🦺 **सुरक्षा उपाय (Safety Measures):**",
                    "• मास्क, दस्ताने पहनें (Wear mask, gloves)",
                    "• बारिश से पहले न छिड़कें (Don't spray before rain)",
                    "• ठंडी जगह स्टोर करें (Store in cool place)"
                ]
            },
            "dosage": {
                "intro": "🧮 **खुराक कैलकुलेटर (Dosage Calculator):**\n",
                "detailed_request": True  # Will calculate based on field size and crop
            },
            "cost": {
                "intro": "💰 **लागत की जानकारी (Cost Information):**\n",
                "content": [
                    "💳 **अनुमानित खर्च (Estimated Cost):**",
                    "• दवा की कीमत: ₹200-800 प्रति एकड़ (Medicine: ₹200-800/acre)",
                    "• छिड़काव खर्च: ₹100-200 प्रति एकड़ (Spraying: ₹100-200/acre)",
                    "• कुल लागत: ₹300-1000 प्रति एकड़ (Total: ₹300-1000/acre)",
                    "",
                    "📊 **लागत की तुलना (Cost Comparison):**",
                    "• जैविक उपचार: 20-30% सस्ता (Organic: 20-30% cheaper)",
                    "• रसायनिक उपचार: तत्काल प्रभाव (Chemical: Immediate effect)",
                    "• मिश्रित दृष्टिकोण: संतुलित लागत (Mixed: Balanced cost)",
                    "",
                    "💡 **बचत के तरीके (Cost Saving Tips):**",
                    "• सामूहिक खरीदारी करें (Group purchasing)",
                    "• सरकारी सब्सिडी की जांच करें (Check govt. subsidies)"
                ]
            },
            "management": {
                "intro": "🌾 **फसल प्रबंधन (Crop Management):**\n",
                "content": [
                    "📅 **दैनिक देखभाल (Daily Care):**",
                    "• सुबह-शाम पानी की जांच (Check water AM/PM)",
                    "• पत्तियों का रंग देखें (Monitor leaf color)",
                    "• कीट-पतंगों की निगरानी (Watch for pests)",
                    "",
                    "🌿 **साप्ताहिक कार्य (Weekly Tasks):**",
                    "• खरपतवार हटाना (Weed removal)",
                    "• मिट्टी की नमी जांचना (Soil moisture check)",
                    "• पोषक तत्वों की आपूर्ति (Nutrient supply)",
                    "",
                    "📊 **मासिक मूल्यांकन (Monthly Assessment):**",
                    "• फसल की वृद्धि दर (Growth rate)",
                    "• उत्पादन का अनुमान (Yield estimation)",
                    "• बाज़ार की कीमतों की जानकारी (Market prices)"
                ]
            },
            "timing": {
                "intro": "⏰ **समय सारणी (Schedule & Timing):**\n",
                "detailed_request": True  # Will create detailed schedule based on crop and season
            },
            "emergency": {
                "intro": "🆘 **आपातकालीन सहायता (Emergency Help):**\n",
                "content": [
                    "🚨 **तत्काल कार्रवाई (Immediate Action):**",
                    "• प्रभावित हिस्से को अलग करें (Isolate affected area)",
                    "• छिड़काव तुरंत बंद करें (Stop spraying immediately)",
                    "• विशेषज्ञ से तुरंत संपर्क करें (Contact expert immediately)",
                    "",
                    "📞 **आपातकालीन संपर्क (Emergency Contacts):**",
                    "• कृषि विशेषज्ञ: +91 85188 00080",
                    "• जिला कृषि अधिकारी से संपर्क करें",
                    "• नजदीकी कृषि सेवा केंद्र जाएं",
                    "",
                    "⚡ **24 घंटे की देखभाल (24-Hour Care):**",
                    "• हर 2 घंटे में जांच करें (Check every 2 hours)",
                    "• पानी की आपूर्ति बनाए रखें (Maintain water supply)",
                    "• फोटो खींचकर प्रगति ट्रैक करें (Track progress with photos)"
                ]
            }
        }

    def detect_follow_up_context(self, user_id: str, limit: int = 10) -> bool:
        """
        Check if user recently received follow-up options after crop analysis.
        Returns True if follow_up_msg was sent in recent conversation.
        """
        recent_messages = get_recent_messages(user_id, limit=limit)
        
        for msg in reversed(recent_messages):
            if (msg.get('is_bot', False) and 
                ('🎯 **[translate:और भी जानकारी चाहिए' in msg.get('message', '') or
                 '🌟 **[translate:आपकी समस्या का समाधान मिल गया है' in msg.get('message', '') or
                 '💬 Aur jaankari ke liye puchiye' in msg.get('message', ''))):  # Backward compatibility
                return True
        
        return False

    def detect_intent(self, message: str) -> Optional[str]:
        """
        Detect user intent from message based on keywords.
        Returns: 'treatment', 'prevention', 'medicine', or None
        """
        message_lower = message.lower().strip()
        
        # Check each intent
        for intent, keywords in self.intent_keywords.items():
            # Check English keywords
            for keyword in keywords["english"]:
                if keyword in message_lower:
                    return intent
            
            # Check Hindi keywords
            for keyword in keywords["hindi"]:
                if keyword in message_lower:
                    return intent
        
        return None

    def generate_response(self, intent: str, crop_type: str = "", disease: str = "", user_id: str = "") -> str:
        """
        Generate appropriate response based on detected intent.
        """
        if intent not in self.response_templates:
            return self._get_fallback_response()
        
        template = self.response_templates[intent]
        response = template["intro"]
        
        # Handle detailed AI-powered responses
        if template.get("detailed_request") and crop_type and user_id:
            try:
                if intent == "treatment":
                    # Use existing Gemini API for detailed treatment
                    detailed_info = get_treatment_followup(disease, crop_type, user_id)
                    response += detailed_info
                elif intent == "dosage":
                    # Generate dosage calculator response
                    response += self._generate_dosage_calculator(crop_type, disease)
                elif intent == "timing":
                    # Generate detailed timing schedule
                    response += self._generate_timing_schedule(crop_type, disease)
                else:
                    response += self._get_detailed_fallback(intent, crop_type)
            except Exception as e:
                response += self._get_detailed_fallback(intent, crop_type)
        
        # Handle predefined content responses
        elif "content" in template:
            for item in template["content"]:
                response += f"{item}\n"
        
        # Add general helpful footer
        response += self._get_response_footer(intent)
        
        return response

    def _get_treatment_fallback(self, crop_type: str) -> str:
        """Fallback treatment response if AI fails."""
        return (
            f"**{crop_type} के लिए सामान्य उपचार:**\n"
            "• Identify the exact disease/pest\n"
            "• Apply appropriate fungicide/pesticide\n"
            "• Maintain proper field hygiene\n"
            "• Monitor progress after treatment\n"
        )

    def _generate_dosage_calculator(self, crop_type: str, disease: str) -> str:
        """Generate dosage calculation based on crop and disease."""
        return (
            f"**{crop_type} के लिए खुराक गणना (Dosage Calculation for {crop_type}):**\n"
            "\n📏 **खेत का क्षेत्रफल (Field Area):**\n"
            "• 1 एकड़ के लिए (For 1 acre): 200-300 ली. पानी\n"
            "• 1 बीघा के लिए (For 1 bigha): 80-120 ली. पानी\n"
            "\n� **दवा की मात्रा (Medicine Quantity):**\n"
            "• कवकनाशी (Fungicide): 2-3 ग्राम प्रति लीटर\n"
            "• कीटनाशी (Insecticide): 1-2 मिली प्रति लीटर\n"
            "• पौष्टिक तत्व (Nutrients): 5-10 ग्राम प्रति लीटर\n"
            "\n⚖️ **मिश्रण अनुपात (Mixing Ratio):**\n"
            "• पहले पानी, फिर दवा मिलाएं\n"
            "• धीरे-धीरे हिलाते रहें\n"
            "• 30 मिनट के अंदर इस्तेमाल करें\n"
        )

    def _generate_timing_schedule(self, crop_type: str, disease: str) -> str:
        """Generate detailed timing schedule for treatment."""
        return (
            f"**{crop_type} के लिए समय सारणी (Schedule for {crop_type}):**\n"
            "\n📅 **साप्ताहिक कार्यक्रम (Weekly Schedule):**\n"
            "• **सोमवार**: खेत की जांच, कीट निगरानी\n"
            "• **बुधवार**: छिड़काव (यदि आवश्यक हो)\n"
            "• **शुक्रवार**: पोषक तत्व प्रबंधन\n"
            "• **रविवार**: साप्ताहिक रिपोर्ट तैयार करना\n"
            "\n🕒 **दैनिक समय (Daily Timing):**\n"
            "• **सुबह 6-8 बजे**: निरीक्षण और पानी देना\n"
            "• **शाम 4-6 बजे**: छिड़काव (यदि आवश्यक)\n"
            "• **रात 8-9 बजे**: अगले दिन की योजना\n"
            "\n⏳ **उपचार की अवधि (Treatment Duration):**\n"
            "• तत्काल राहत: 3-5 दिन\n"
            "• पूर्ण उपचार: 10-15 दिन\n"
            "• पुनरावृत्ति रोकथाम: 21-30 दिन\n"
        )

    def _get_detailed_fallback(self, intent: str, crop_type: str) -> str:
        """Fallback for detailed requests when AI fails."""
        fallbacks = {
            "dosage": f"{crop_type} के लिए मानक खुराक की जानकारी उपलब्ध नहीं है। कृपया स्थानीय विशेषज्ञ से संपर्क करें।",
            "timing": f"{crop_type} के लिए सामान्य समय सारणी: सुबह निरीक्षण, दिन में देखभाल, शाम को उपचार।",
        }
        return fallbacks.get(intent, f"{crop_type} के लिए विस्तृत जानकारी उपलब्ध नहीं है।")

    def _get_response_footer(self, intent: str) -> str:
        """Add helpful footer to responses."""
        footers = {
            "treatment": "\n📞 **व्यक्तिगत सलाह**: +91 85188 00080",
            "prevention": "\n🌱 **याद रखें**: रोकथाम इलाज से बेहतर है!",
            "medicine": "\n⚠️ **सावधानी**: विशिष्ट खुराक के लिए विशेषज्ञ से सलाह लें",
            "dosage": "\n🧮 **नोट**: खेत के आकार के अनुसार मात्रा समायोजित करें",
            "cost": "\n💡 **सुझाव**: सामूहिक खरीदारी से बचत करें",
            "management": "\n📊 **ट्रैकिंग**: दैनिक प्रगति का रिकॉर्ड रखें",
            "timing": "\n⏰ **लचीलापन**: मौसम के अनुसार समय बदलें",
            "emergency": "\n🆘 **24/7 हेल्पलाइन**: +91 85188 00080"
        }
        return footers.get(intent, "\n💚 **खुश किसानी**: सफल खेती की शुभकामनाएं!")

    def _get_fallback_response(self) -> str:
        """Fallback response when intent is not detected."""
        return (
            "🤔 **[translate:मैं आपकी बात समझ नहीं पाया]** (I didn't understand your request)\n\n"
            "🎯 **[translate:कृपया इनमें से कोई शब्द टाइप करें]** (Please type one of these words):\n\n"
            
            "💊 **उपचार**: 'उपचार' या 'treatment'\n"
            "🛡️ **बचाव**: 'रोकथाम' या 'prevention'\n"
            "🧪 **दवा**: 'दवा' या 'medicine'\n"
            "🧮 **खुराक**: 'खुराक' या 'dosage'\n"
            "💰 **कीमत**: 'कीमत' या 'cost'\n"
            "🌾 **प्रबंधन**: 'प्रबंधन' या 'management'\n"
            "⏰ **समय**: 'समय' या 'timing'\n"
            "🆘 **तुरंत**: 'तुरंत' या 'urgent'\n\n"
            
            "📞 **[translate:व्यक्तिगत सहायता]**: +91 85188 00080"
        )

    def should_handle_message(self, user_id: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if this message should be handled as a follow-up.
        Returns: (should_handle, detected_intent)
        """
        # Check if user is in follow-up context
        if not self.detect_follow_up_context(user_id):
            return False, None
        
        # Detect intent
        intent = self.detect_intent(message)
        
        return intent is not None, intent

    def get_last_analysis_info(self, user_id: str) -> Dict[str, str]:
        """
        Get information about the last crop analysis for context.
        Returns dict with crop_type and disease info.
        """
        recent_messages = get_recent_messages(user_id, limit=15)
        
        crop_type = ""
        disease = ""
        
        # Look for recent analysis results
        for msg in reversed(recent_messages):
            message_text = msg.get('message', '')
            
            # Extract crop type from analysis
            if 'Crop Type:' in message_text or 'फसल:' in message_text:
                lines = message_text.split('\n')
                for line in lines:
                    if 'Crop Type:' in line or 'फसल:' in line:
                        crop_type = line.split(':')[-1].strip()
                        break
            
            # Extract disease info
            if 'Disease:' in message_text or 'बीमारी:' in message_text:
                lines = message_text.split('\n')
                for line in lines:
                    if 'Disease:' in line or 'बीमारी:' in line:
                        disease = line.split(':')[-1].strip()
                        break
        
        return {"crop_type": crop_type, "disease": disease}


# Create global instance
follow_up_handler = FollowUpHandler()