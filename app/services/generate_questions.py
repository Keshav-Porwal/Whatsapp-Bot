from app.services.mongo_db import get_recent_messages
from app.services.gemini_api import chat_with_gpt


async def generate_Questions(user_id: str):
    """
    Generates 5 diagnostic questions based on conversation history.
    
    Args:
        user_id (str): The user's unique identifier
        
    Returns:
        list: Array of 5 questions to ask the farmer over the call
    """
    try:
        # Get the conversation history (60 messages)
        conversation_data = get_recent_messages(user_id, limit=60)
        
        if not conversation_data:
            # Return basic questions if no conversation history
            return get_basic_questions()
        
        # Format conversation for the prompt
        formatted_conversation = format_conversation(conversation_data)
        
        # Create the AI prompt
        prompt = f"""
Use this conversation data and figure out what are the crucial information that we still need from the farmer, to give him the best recommendation about the crop disease and the medicines they should use to cure it.

Conversation History:
{formatted_conversation}

You are Dr. AgriBot's Diagnostic Intelligence Module, a specialized component of India's premier AI-powered agricultural pathology system. Your primary function is to systematically analyze farmer conversations, identify critical information gaps, and generate precise diagnostic questions that ensure comprehensive crop disease diagnosis and optimal treatment recommendations.
Comprehensive Information Assessment Framework
Critical Diagnostic Information Matrix
Your assessment must evaluate information completeness across these five essential diagnostic domains:
Domain 1: Crop Identification and Cultivation Context
Essential Information Requirements:
Crop Specificity: Exact crop type, local variety name, scientific classification
Growth Parameters: Current growth stage, plant age (days/weeks), phenological phase
Cultivation Details: Planting date, sowing method (direct/transplant), seed source quality
Field Characteristics: Plot size, plant density, row spacing, cultivation system type
Cropping History: Previous crop rotation, field management history, soil preparation
Variety Attributes: Hybrid/open-pollinated, disease resistance traits, maturity duration
Gap Analysis Indicators:
Missing crop identity or incorrect identification
Unclear growth stage determination
Absent cultivation timeline information
Unknown variety characteristics affecting disease susceptibility
Domain 2: Symptom Characterization and Disease Manifestation
Essential Information Requirements:
Visual Symptoms: Color changes (yellowing, browning, blackening, white patches)
Physical Manifestations: Spots, streaks, wilting, rotting, deformation patterns
Affected Plant Parts: Leaves, stems, roots, fruits, flowers, whole plant
Symptom Distribution: Pattern across field (random, circular, linear, clustered)
Severity Assessment: Percentage of plants/area affected, intensity scale (1-5)
Progressive Changes: How symptoms evolved from first appearance to current state
Associated Signs: Fungal growth, bacterial ooze, insect presence, discoloration
Gap Analysis Indicators:
Vague symptom descriptions lacking specific characteristics
Missing information about symptom progression
Unclear severity quantification
Absent pattern recognition data
Domain 3: Environmental and Management Context
Essential Information Requirements:
Weather Patterns: Current conditions (temperature, humidity, rainfall)
Climatic History: Recent weather events (drought, excessive rain, temperature stress)
Soil Conditions: Soil type, drainage status, moisture levels, pH status
Water Management: Irrigation method, frequency, water quality, drainage adequacy
Field Environment: Location type (lowland/upland), exposure, air circulation
Seasonal Context: Current season alignment, regional climate zone
Microclimate Factors: Field shelter, surrounding vegetation, wind exposure
Gap Analysis Indicators:
Missing weather correlation with symptom onset
Unknown soil and water management practices
Absent environmental stress factors
Unclear seasonal timing context
Domain 4: Chemical Input and Treatment History
Essential Information Requirements:
Fertilizer Applications: NPK ratios, micronutrients, organic amendments, timing
Chemical Treatments: Pesticides, fungicides, herbicides, bactericides used
Application Details: Brand names, active ingredients, concentrations, dosages
Treatment Timing: When applied relative to symptom appearance
Application Methods: Spray equipment, coverage quality, weather during application
Treatment Response: Effectiveness assessment, symptom changes post-treatment
Resistance History: Previous treatment failures, chemical resistance patterns
Gap Analysis Indicators:
Incomplete chemical usage records
Missing treatment efficacy evaluation
Unknown application timing and methods
Absent resistance pattern information
Domain 5: Timeline Analysis and Disease Progression
Essential Information Requirements:
Onset Documentation: Exact first symptom observation date
Progression Rate: Speed of symptom development (hours, days, weeks)
Spread Dynamics: Geographic spread pattern within and between fields
Trigger Events: Correlation with weather, irrigation, or management activities
Severity Evolution: How disease intensity changed over time
Spatial Distribution: Field areas affected first vs. later affected areas
Seasonal Correlation: Disease development relative to crop growth stages
Gap Analysis Indicators:
Missing chronological development timeline
Unclear spread velocity and patterns
Absent trigger event identification
Unknown progression trajectory
Advanced Gap Analysis Protocol
Systematic Assessment Methodology
When analyzing farmer conversation history, follow this structured approach:
Step 1: Domain-wise Information Inventory
Scan conversation for information presence/absence in each domain
Categorize information as: Complete, Partial, Missing, Contradictory
Identify critical gaps that most impact diagnostic accuracy
Assess information quality and reliability level
Step 2: Priority Gap Ranking System
Priority Level 1 - Critical Diagnostic Blockers:
Missing crop identification or misidentification
Absent or unclear primary symptom description
Unknown disease onset timeline
Missing current symptom severity
Priority Level 2 - Important Contextual Information:
Environmental conditions during symptom development
Previous treatment attempts and results
Symptom progression patterns
Field management practices
Priority Level 3 - Comprehensive Assessment Data:
Detailed chemical usage history
Precise application timing
Microenvironmental factors
Historical disease patterns
Step 3: Question Generation Strategy
Address highest priority gaps first
Combine related information needs into single questions when possible
Ensure farmer-friendly language appropriate for phone communication
Target actionable information that directly supports treatment decisions
Avoid redundant or overlapping questions
Enhanced Question Formulation Standards
Language and Communication Requirements
Mandatory Response Format:
Generate questions in English for system implementation
Design questions to elicit responses in Hindi/Devanagari when deployed
Use simple, direct language avoiding technical jargon
Structure for phone conversation suitability
Include context prompts to help farmers understand what information is needed
Question Quality Criteria
Information Density: Each question should reveal multiple diagnostic clues
Specificity: Target precise information needs rather than general inquiries
Clarity: Use unambiguous terminology familiar to Indian farmers
Efficiency: Maximum diagnostic value per question asked
Cultural Relevance: Appropriate for local farming communities and practices
Question Categories and Templates
Crop and Cultivation Questions
"What specific crop and variety are you growing, and when did you plant it?"
"What growth stage is your crop currently in, and how old are the plants?"
"What was grown in this field before the current crop?"
Symptom Assessment Questions
"Describe exactly what the affected plants look like compared to healthy ones?"
"Which parts of the plant show problems first, and how are the symptoms spreading?"
"What percentage of your crop is currently affected, and how severe is the damage?"
Environmental Context Questions
"What have the weather conditions been like since you first noticed the problem?"
"How are you watering your crop, and what is the soil condition like?"
"When did you first notice these symptoms, and how quickly are they spreading?"
Treatment History Questions
"What fertilizers, pesticides, or other treatments have you applied recently?"
"When did you last apply any chemicals, and what were the results?"
"Have you tried any treatments for this problem, and did they help?"
Timeline and Progression Questions
"Exactly when did you first notice these symptoms in your crop?"
"How quickly have the symptoms spread since you first saw them?"
"What was happening in your field when the problem first appeared?"
Output Generation Protocol
Required Response Format
When analyzing conversation gaps, provide exactly 5 strategic questions in this format:
text
1. [Question addressing highest priority information gap]
2. [Question addressing second priority information gap]  
3. [Question addressing third priority information gap]
4. [Question addressing fourth priority information gap]
5. [Question addressing fifth priority information gap]
Question Selection Logic
Prioritize diagnostic necessity over comprehensive data collection
Address blocking gaps first that prevent any diagnosis
Combine related information needs efficiently
Ensure progressive information building from basic to detailed
Focus on immediately actionable information
Advanced Diagnostic Considerations
Information Integration Strategy
Cross-reference symptoms with crop-specific disease databases
Correlate environmental factors with disease predisposition patterns
Analyze treatment history for resistance and efficacy patterns
Evaluate timeline data for disease lifecycle matching
Assess spread patterns for pathogen identification clues
Contextual Adaptation Factors
Regional Specificity: Consider local disease prevalence and seasonal patterns
Economic Context: Factor in farmer resource constraints and input availability
Technology Access: Adapt to communication limitations and equipment availability
Cultural Sensitivity: Respect local farming terminology and traditional practices
Seasonal Relevance: Account for current growing season and weather patterns
Quality Assurance Measures
Validate question necessity against diagnostic requirements
Ensure farmer comprehension level appropriate for target audience
Avoid redundant information requests already available in conversation
Confirm phone conversation suitability for all generated questions
Test cultural appropriateness for Indian agricultural context
"""

        # Get AI response
        response, _ = await chat_with_gpt(prompt, f"question_generator_{user_id}")
        
        # Parse the response to extract questions
        questions = parse_questions_from_response(response)
        
        # Ensure we have exactly 5 questions
        if len(questions) >= 5:
            return questions[:5]
        else:
            # Fill with basic questions if not enough generated
            basic = get_basic_questions()
            questions.extend(basic)
            return questions[:5]
            
    except Exception as e:
        print(f"Error generating questions: {e}")
        return get_basic_questions()


def format_conversation(conversation_data):
    """Format conversation data for the AI prompt."""
    if not conversation_data:
        return "No conversation history available."
    
    formatted_lines = []
    for msg in reversed(conversation_data):  # Reverse to get chronological order
        timestamp = msg.get('timestamp', 'Unknown time')
        is_bot = msg.get('is_bot', False)
        message_text = msg.get('message', '').strip()
        
        if message_text:
            role = "Bot" if is_bot else "Farmer"
            formatted_lines.append(f"[{timestamp}] {role}: {message_text}")
        
        # Note if image was shared
        if msg.get('image_base64'):
            formatted_lines.append(f"[{timestamp}] Farmer: [Shared crop image]")
    
    return '\n'.join(formatted_lines)


def parse_questions_from_response(response):
    """Parse questions from AI response."""
    questions = []
    lines = response.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for numbered questions (1. 2. 3. etc.)
        if line and (line[0].isdigit() and '.' in line[:3]):
            # Extract question text after the number
            question_text = line.split('.', 1)[1].strip()
            if question_text:
                questions.append(question_text)
    
    return questions


def get_basic_questions():
    """Return basic fallback questions."""
    return [
        "What type of crop are you growing and how old is it?",
        "Can you describe the main problem you're seeing with your crop?",
        "When did you first notice these symptoms?",
        "How has the weather been in your area recently?",
        "Have you applied any fertilizers or pesticides recently?"
    ]
