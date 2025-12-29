#!/usr/bin/env python3
"""
Complete Legal Assistant Workflow - Three Stage System
=======================================================
A Telegram bot implementing the full client journey:
  Stage 1: Client Interview (fact gathering)
  Stage 2: Legal Draft (document generation)  
  Stage 3: Advocate Recommendation (matching)

This builds upon the advocate-skill integration and adds a custom
recommend_advocates tool that matches clients with appropriate legal
professionals based on case characteristics collected during earlier stages.
"""

import os
import logging
import asyncio
import tempfile
import base64
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ADVOCATE_SKILL_ID = os.getenv("ADVOCATE_SKILL_ID", "skill_01Jm6n7UWuv5w168KjwuUEyS")

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
SKILLS_BETAS = ["code-execution-2025-08-25", "skills-2025-10-02", "files-api-2025-04-14"]
MAX_HISTORY_MESSAGES = 20
MAX_PAUSE_RETRIES = 10
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG_MODE else logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# ADVOCATE REGISTRY DATABASE
# =============================================================================
# In production, this would be a proper database (PostgreSQL, MongoDB, etc.)
# For now, we use an in-memory registry that demonstrates the full structure.

@dataclass
class AdvocateProfile:
    """
    Represents a registered advocate with all matching-relevant attributes.
    
    The structure mirrors how a real law firm directory would organize
    information about its lawyers, capturing everything needed for
    intelligent case-to-advocate matching.
    """
    advocate_id: str
    name: str
    enrollment_number: str  # Bar Council enrollment
    enrollment_year: int
    
    # Geographic availability
    practicing_states: List[str]  # States where they can appear
    practicing_districts: List[str]  # Preferred districts
    home_court: str  # Primary court of practice
    
    # Specialization areas (maps to document types in advocate-skill)
    specializations: List[str]  # e.g., ["civil", "matrimonial", "property"]
    sub_specializations: List[str]  # e.g., ["Section 138 NI Act", "RERA disputes"]
    
    # Experience indicators
    years_of_practice: int
    landmark_cases: int  # Number of reported judgments
    success_rate_category: str  # "excellent", "good", "average"
    
    # Capacity and availability
    current_case_load: int
    max_case_load: int
    available_for_new_cases: bool
    
    # Fee structure
    fee_category: str  # "premium", "standard", "affordable", "pro_bono"
    consultation_fee: Optional[int]  # In INR, None if free
    
    # Languages
    languages: List[str]  # Languages advocate can work in
    
    # Contact and additional info
    contact_phone: str
    contact_email: str
    office_address: str
    
    # Metadata
    rating: float  # 1.0 to 5.0
    total_reviews: int
    verified: bool
    last_updated: datetime = field(default_factory=datetime.now)


# Sample advocate registry - in production, load from database
ADVOCATE_REGISTRY: Dict[str, AdvocateProfile] = {
    "ADV001": AdvocateProfile(
        advocate_id="ADV001",
        name="Adv. Rajesh Kumar Sharma",
        enrollment_number="D/1234/2005",
        enrollment_year=2005,
        practicing_states=["Delhi", "Haryana", "Punjab"],
        practicing_districts=["Central Delhi", "South Delhi", "Gurugram"],
        home_court="Delhi High Court",
        specializations=["civil", "constitutional", "property"],
        sub_specializations=["Writ Petitions", "Land Acquisition", "RERA"],
        years_of_practice=19,
        landmark_cases=12,
        success_rate_category="excellent",
        current_case_load=28,
        max_case_load=40,
        available_for_new_cases=True,
        fee_category="premium",
        consultation_fee=5000,
        languages=["Hindi", "English", "Punjabi"],
        contact_phone="+91-98765-43210",
        contact_email="rajesh.sharma@example.com",
        office_address="Chamber No. 215, Delhi High Court, New Delhi",
        rating=4.8,
        total_reviews=156,
        verified=True
    ),
    "ADV002": AdvocateProfile(
        advocate_id="ADV002",
        name="Adv. Priya Mehta",
        enrollment_number="MH/5678/2012",
        enrollment_year=2012,
        practicing_states=["Maharashtra", "Goa"],
        practicing_districts=["Mumbai City", "Mumbai Suburban", "Thane", "Pune"],
        home_court="Bombay High Court",
        specializations=["matrimonial", "criminal", "civil"],
        sub_specializations=["Divorce", "Domestic Violence", "Maintenance", "Bail"],
        years_of_practice=12,
        landmark_cases=5,
        success_rate_category="excellent",
        current_case_load=22,
        max_case_load=35,
        available_for_new_cases=True,
        fee_category="standard",
        consultation_fee=2000,
        languages=["Hindi", "English", "Marathi", "Gujarati"],
        contact_phone="+91-98765-12345",
        contact_email="priya.mehta@example.com",
        office_address="Office 401, Lawyers Tower, Fort, Mumbai",
        rating=4.6,
        total_reviews=98,
        verified=True
    ),
    "ADV003": AdvocateProfile(
        advocate_id="ADV003",
        name="Adv. Mohammed Hussain",
        enrollment_number="KA/2345/2008",
        enrollment_year=2008,
        practicing_states=["Karnataka", "Tamil Nadu", "Kerala"],
        practicing_districts=["Bangalore Urban", "Bangalore Rural", "Chennai"],
        home_court="Karnataka High Court",
        specializations=["criminal", "civil", "constitutional"],
        sub_specializations=["Bail Applications", "Section 138 NI Act", "Anticipatory Bail"],
        years_of_practice=16,
        landmark_cases=8,
        success_rate_category="excellent",
        current_case_load=30,
        max_case_load=40,
        available_for_new_cases=True,
        fee_category="standard",
        consultation_fee=3000,
        languages=["English", "Kannada", "Tamil", "Hindi", "Urdu"],
        contact_phone="+91-98765-67890",
        contact_email="m.hussain@example.com",
        office_address="Chamber No. 112, Karnataka High Court, Bangalore",
        rating=4.7,
        total_reviews=134,
        verified=True
    ),
    "ADV004": AdvocateProfile(
        advocate_id="ADV004",
        name="Adv. Sunita Devi",
        enrollment_number="UP/8901/2015",
        enrollment_year=2015,
        practicing_states=["Uttar Pradesh", "Uttarakhand"],
        practicing_districts=["Lucknow", "Kanpur", "Allahabad", "Varanasi"],
        home_court="Allahabad High Court",
        specializations=["property", "conveyancing", "civil"],
        sub_specializations=["Sale Deeds", "Partition", "Title Disputes", "Will Probate"],
        years_of_practice=9,
        landmark_cases=2,
        success_rate_category="good",
        current_case_load=18,
        max_case_load=30,
        available_for_new_cases=True,
        fee_category="affordable",
        consultation_fee=1000,
        languages=["Hindi", "English"],
        contact_phone="+91-98765-11111",
        contact_email="sunita.devi@example.com",
        office_address="Advocates Complex, Civil Lines, Lucknow",
        rating=4.3,
        total_reviews=67,
        verified=True
    ),
    "ADV005": AdvocateProfile(
        advocate_id="ADV005",
        name="Adv. Arjun Nair",
        enrollment_number="KL/6789/2010",
        enrollment_year=2010,
        practicing_states=["Kerala", "Karnataka"],
        practicing_districts=["Ernakulam", "Thiruvananthapuram", "Kozhikode"],
        home_court="Kerala High Court",
        specializations=["civil", "property", "conveyancing"],
        sub_specializations=["Land Disputes", "Partition Suits", "Injunctions"],
        years_of_practice=14,
        landmark_cases=6,
        success_rate_category="excellent",
        current_case_load=25,
        max_case_load=35,
        available_for_new_cases=True,
        fee_category="standard",
        consultation_fee=2500,
        languages=["English", "Malayalam", "Hindi", "Tamil"],
        contact_phone="+91-98765-22222",
        contact_email="arjun.nair@example.com",
        office_address="High Court Advocates Block, Ernakulam, Kochi",
        rating=4.5,
        total_reviews=89,
        verified=True
    ),
    "ADV006": AdvocateProfile(
        advocate_id="ADV006",
        name="Adv. Deepika Singh Rathore",
        enrollment_number="RJ/3456/2016",
        enrollment_year=2016,
        practicing_states=["Rajasthan", "Madhya Pradesh"],
        practicing_districts=["Jaipur", "Jodhpur", "Udaipur"],
        home_court="Rajasthan High Court",
        specializations=["matrimonial", "civil", "criminal"],
        sub_specializations=["Divorce", "Child Custody", "Maintenance", "DV Act"],
        years_of_practice=8,
        landmark_cases=3,
        success_rate_category="good",
        current_case_load=20,
        max_case_load=30,
        available_for_new_cases=True,
        fee_category="affordable",
        consultation_fee=1500,
        languages=["Hindi", "English", "Rajasthani"],
        contact_phone="+91-98765-33333",
        contact_email="deepika.rathore@example.com",
        office_address="Advocates Chambers, High Court Campus, Jaipur",
        rating=4.4,
        total_reviews=56,
        verified=True
    ),
    "ADV007": AdvocateProfile(
        advocate_id="ADV007",
        name="Adv. Vikram Choudhury",
        enrollment_number="WB/4567/2000",
        enrollment_year=2000,
        practicing_states=["West Bengal", "Jharkhand", "Odisha"],
        practicing_districts=["Kolkata", "Howrah", "North 24 Parganas"],
        home_court="Calcutta High Court",
        specializations=["constitutional", "civil", "criminal"],
        sub_specializations=["PIL", "Writ Petitions", "Service Matters", "Land Acquisition"],
        years_of_practice=24,
        landmark_cases=18,
        success_rate_category="excellent",
        current_case_load=32,
        max_case_load=40,
        available_for_new_cases=True,
        fee_category="premium",
        consultation_fee=7500,
        languages=["Bengali", "English", "Hindi"],
        contact_phone="+91-98765-44444",
        contact_email="vikram.choudhury@example.com",
        office_address="Senior Advocates Block, Calcutta High Court, Kolkata",
        rating=4.9,
        total_reviews=203,
        verified=True
    ),
    "ADV008": AdvocateProfile(
        advocate_id="ADV008",
        name="Adv. Kavitha Reddy",
        enrollment_number="TS/7890/2014",
        enrollment_year=2014,
        practicing_states=["Telangana", "Andhra Pradesh"],
        practicing_districts=["Hyderabad", "Rangareddy", "Secunderabad"],
        home_court="Telangana High Court",
        specializations=["civil", "property", "constitutional"],
        sub_specializations=["RERA", "Real Estate Disputes", "Builder Disputes"],
        years_of_practice=10,
        landmark_cases=4,
        success_rate_category="good",
        current_case_load=24,
        max_case_load=35,
        available_for_new_cases=True,
        fee_category="standard",
        consultation_fee=2000,
        languages=["Telugu", "English", "Hindi"],
        contact_phone="+91-98765-55555",
        contact_email="kavitha.reddy@example.com",
        office_address="Advocates Complex, High Court Road, Hyderabad",
        rating=4.4,
        total_reviews=72,
        verified=True
    ),
    "ADV009": AdvocateProfile(
        advocate_id="ADV009",
        name="Adv. Gurpreet Singh Bedi",
        enrollment_number="PB/5432/2011",
        enrollment_year=2011,
        practicing_states=["Punjab", "Haryana", "Chandigarh"],
        practicing_districts=["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar"],
        home_court="Punjab and Haryana High Court",
        specializations=["criminal", "civil", "property"],
        sub_specializations=["NDPS", "Bail", "Anticipatory Bail", "Murder Cases"],
        years_of_practice=13,
        landmark_cases=7,
        success_rate_category="excellent",
        current_case_load=28,
        max_case_load=35,
        available_for_new_cases=True,
        fee_category="standard",
        consultation_fee=3500,
        languages=["Punjabi", "Hindi", "English"],
        contact_phone="+91-98765-66666",
        contact_email="gurpreet.bedi@example.com",
        office_address="Sector 17, High Court Complex, Chandigarh",
        rating=4.6,
        total_reviews=118,
        verified=True
    ),
    "ADV010": AdvocateProfile(
        advocate_id="ADV010",
        name="Adv. Fatima Khan",
        enrollment_number="MP/2109/2017",
        enrollment_year=2017,
        practicing_states=["Madhya Pradesh", "Chhattisgarh"],
        practicing_districts=["Bhopal", "Indore", "Jabalpur"],
        home_court="Madhya Pradesh High Court",
        specializations=["matrimonial", "civil"],
        sub_specializations=["Muslim Personal Law", "Maintenance", "Mehr Recovery"],
        years_of_practice=7,
        landmark_cases=1,
        success_rate_category="good",
        current_case_load=15,
        max_case_load=25,
        available_for_new_cases=True,
        fee_category="affordable",
        consultation_fee=1000,
        languages=["Hindi", "English", "Urdu"],
        contact_phone="+91-98765-77777",
        contact_email="fatima.khan@example.com",
        office_address="Advocates Building, M.P. High Court, Jabalpur",
        rating=4.2,
        total_reviews=45,
        verified=True
    ),
}


# =============================================================================
# CASE PROFILE - EXTRACTED FROM INTERVIEW AND DRAFT STAGES
# =============================================================================

@dataclass
class CaseProfile:
    """
    Represents the distilled case characteristics extracted from the client
    interview and document drafting stages. This profile drives the advocate
    matching algorithm.
    
    Think of this as a "case summary card" that captures everything needed
    to find the right advocate: what type of matter it is, where it will be
    filed, how complex it seems, and any special requirements the client has.
    """
    # Basic classification
    matter_type: str  # "civil", "matrimonial", "criminal", "property", "constitutional"
    sub_category: str  # Specific document type or legal issue

    # Geographic jurisdiction
    state: str
    district: str
    court_level: str  # "district", "high_court", "supreme_court", "tribunal"

    # Complexity indicators
    estimated_complexity: str  # "simple", "moderate", "complex", "highly_complex"

    # Optional fields with defaults
    specific_court: Optional[str] = None
    number_of_parties: int = 2
    amount_in_dispute: Optional[int] = None  # In INR
    involves_multiple_reliefs: bool = False

    # Urgency
    urgency_level: str = "normal"  # "urgent", "normal", "can_wait"
    limitation_concern: bool = False  # Whether limitation period is a concern
    
    # Client preferences
    preferred_languages: List[str] = field(default_factory=lambda: ["Hindi", "English"])
    budget_category: str = "standard"  # "premium", "standard", "affordable", "pro_bono"
    
    # Additional requirements
    requires_senior_counsel: bool = False
    requires_specific_expertise: List[str] = field(default_factory=list)
    
    # Extracted key facts for advocate briefing
    key_facts_summary: str = ""
    
    # Timestamp
    extracted_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# RECOMMEND ADVOCATES TOOL - THE MATCHING ENGINE
# =============================================================================

def recommend_advocates_tool_schema() -> dict:
    """
    Defines the JSON schema for the recommend_advocates tool.
    
    This tool is invoked by Claude after completing the interview and draft
    stages. It takes the case profile as structured input and returns
    matching advocates ranked by suitability.
    
    The schema is intentionally detailed because good tool descriptions
    lead to better tool usage by Claude. Each parameter includes clear
    descriptions of expected values and how they affect matching.
    """
    return {
        "name": "recommend_advocates",
        "description": """Recommends suitable advocates for a legal matter based on case characteristics.
        
This tool should be used AFTER completing the client interview and document drafting stages.
It matches the case profile against the advocate registry to find the most suitable legal
professionals based on:

1. SPECIALIZATION MATCH: Advocate's practice areas vs case matter type
2. GEOGRAPHIC AVAILABILITY: Where the advocate can appear vs where case will be filed
3. EXPERIENCE LEVEL: Years of practice and case complexity requirements
4. CAPACITY: Current workload and availability for new cases
5. FEE STRUCTURE: Client's budget vs advocate's fee category
6. LANGUAGE: Client's preferred languages vs advocate's working languages

The tool returns a ranked list of recommended advocates with match scores and
reasons for each recommendation. Always present at least the top 3 matches
to give the client meaningful choices.""",
        
        "input_schema": {
            "type": "object",
            "properties": {
                "matter_type": {
                    "type": "string",
                    "enum": ["civil", "matrimonial", "criminal", "property", "constitutional", "conveyancing", "notice"],
                    "description": "Primary type of legal matter. Determines which specialists to consider."
                },
                "sub_category": {
                    "type": "string",
                    "description": "Specific type of document or legal issue within the matter type. Examples: 'divorce petition', 'bail application', 'sale deed', 'Section 138 complaint'"
                },
                "state": {
                    "type": "string",
                    "description": "Indian state where the case will be filed. Must match advocate's practicing states."
                },
                "district": {
                    "type": "string",
                    "description": "District where the case will be filed. Helps identify advocates with local expertise."
                },
                "court_level": {
                    "type": "string",
                    "enum": ["district", "high_court", "supreme_court", "tribunal"],
                    "description": "Level of court where case will be filed. Affects experience requirements."
                },
                "estimated_complexity": {
                    "type": "string",
                    "enum": ["simple", "moderate", "complex", "highly_complex"],
                    "description": "Estimated complexity based on facts gathered during interview."
                },
                "urgency_level": {
                    "type": "string",
                    "enum": ["urgent", "normal", "can_wait"],
                    "description": "How urgently the client needs representation."
                },
                "preferred_languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Languages the client is comfortable communicating in."
                },
                "budget_category": {
                    "type": "string",
                    "enum": ["premium", "standard", "affordable", "pro_bono"],
                    "description": "Client's budget constraints for legal fees."
                },
                "amount_in_dispute": {
                    "type": "integer",
                    "description": "Amount in dispute in INR. Affects court level and advocate experience needs."
                },
                "requires_senior_counsel": {
                    "type": "boolean",
                    "description": "Whether the case complexity warrants a senior advocate."
                },
                "specific_expertise_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific legal expertise required. Examples: 'RERA', 'NDPS', 'Section 138'"
                },
                "key_facts_summary": {
                    "type": "string",
                    "description": "Brief summary of key facts for advocate briefing. 2-3 sentences max."
                }
            },
            "required": ["matter_type", "state", "district", "court_level"]
        }
    }


def calculate_advocate_match_score(
    advocate: AdvocateProfile,
    case_profile: Dict[str, Any]
) -> Tuple[float, List[str]]:
    """
    Calculates a match score between an advocate and a case profile.
    
    The algorithm weights different factors based on their importance for
    successful representation. Geographic availability and specialization
    are must-haves (hard filters), while other factors contribute to the
    overall score.
    
    Returns:
        Tuple of (score 0.0-100.0, list of match reasons)
    
    The scoring breakdown:
    - Specialization match: 30 points max
    - Geographic match: 25 points max (also a hard filter)
    - Experience alignment: 15 points max
    - Availability: 10 points max
    - Fee alignment: 10 points max
    - Language match: 5 points max
    - Rating bonus: 5 points max
    """
    score = 0.0
    reasons = []
    
    # Extract case parameters with defaults
    matter_type = case_profile.get("matter_type", "")
    sub_category = case_profile.get("sub_category", "")
    state = case_profile.get("state", "")
    district = case_profile.get("district", "")
    court_level = case_profile.get("court_level", "district")
    complexity = case_profile.get("estimated_complexity", "moderate")
    urgency = case_profile.get("urgency_level", "normal")
    languages = case_profile.get("preferred_languages", ["Hindi", "English"])
    budget = case_profile.get("budget_category", "standard")
    requires_senior = case_profile.get("requires_senior_counsel", False)
    specific_expertise = case_profile.get("specific_expertise_needed", [])
    
    # =================
    # HARD FILTERS
    # =================
    
    # Geographic availability is a must
    if state not in advocate.practicing_states:
        return 0.0, ["Not available in " + state]
    
    # Must be available for new cases
    if not advocate.available_for_new_cases:
        return 0.0, ["Currently not accepting new cases"]
    
    # =================
    # SPECIALIZATION MATCH (30 points)
    # =================
    
    # Primary specialization match
    if matter_type in advocate.specializations:
        score += 20
        reasons.append(f"Specializes in {matter_type} matters")
        
        # Bonus for exact sub-specialization match
        for expertise in specific_expertise:
            if any(expertise.lower() in sub.lower() for sub in advocate.sub_specializations):
                score += 5
                reasons.append(f"Expert in {expertise}")
                break
        
        # Sub-category alignment
        if sub_category:
            for sub in advocate.sub_specializations:
                if sub_category.lower() in sub.lower() or sub.lower() in sub_category.lower():
                    score += 5
                    reasons.append(f"Handles {sub_category} cases regularly")
                    break
    else:
        # Partial match if sub-specializations align
        for expertise in specific_expertise:
            if any(expertise.lower() in sub.lower() for sub in advocate.sub_specializations):
                score += 10
                reasons.append(f"Has experience with {expertise}")
                break
    
    # =================
    # GEOGRAPHIC MATCH (25 points)
    # =================
    
    # State match already confirmed, give base points
    score += 10
    reasons.append(f"Practices in {state}")
    
    # District familiarity bonus
    if district in advocate.practicing_districts:
        score += 10
        reasons.append(f"Familiar with {district} courts")
    
    # Home court bonus for high court cases
    if court_level == "high_court":
        if state.lower() in advocate.home_court.lower():
            score += 5
            reasons.append(f"Home court is {advocate.home_court}")
    
    # =================
    # EXPERIENCE ALIGNMENT (15 points)
    # =================
    
    # Map complexity to minimum years requirement
    complexity_requirements = {
        "simple": 3,
        "moderate": 5,
        "complex": 10,
        "highly_complex": 15
    }
    
    min_years = complexity_requirements.get(complexity, 5)
    
    if advocate.years_of_practice >= min_years:
        # Calculate experience score based on how much they exceed minimum
        experience_score = min(15, 8 + (advocate.years_of_practice - min_years) * 0.5)
        score += experience_score
        reasons.append(f"{advocate.years_of_practice} years of practice")
    else:
        score += 5  # Still some points for trying
    
    # Senior counsel requirement
    if requires_senior and advocate.years_of_practice >= 15:
        score += 5
        reasons.append("Senior counsel experience")
    
    # Court level experience
    if court_level == "high_court" and advocate.landmark_cases > 5:
        score += 3
        reasons.append(f"{advocate.landmark_cases} reported judgments")
    
    # =================
    # AVAILABILITY (10 points)
    # =================
    
    workload_ratio = advocate.current_case_load / advocate.max_case_load
    
    if workload_ratio < 0.5:
        score += 10
        reasons.append("Excellent availability")
    elif workload_ratio < 0.7:
        score += 7
        reasons.append("Good availability")
    elif workload_ratio < 0.9:
        score += 4
        reasons.append("Moderate availability")
    else:
        score += 2
        if urgency == "urgent":
            score -= 5  # Penalty for urgent cases when advocate is busy
    
    # =================
    # FEE ALIGNMENT (10 points)
    # =================
    
    fee_mapping = {
        "pro_bono": ["affordable", "pro_bono"],
        "affordable": ["affordable", "standard"],
        "standard": ["standard", "affordable", "premium"],
        "premium": ["premium", "standard"]
    }
    
    acceptable_fees = fee_mapping.get(budget, ["standard"])
    
    if advocate.fee_category in acceptable_fees:
        if advocate.fee_category == budget:
            score += 10
            reasons.append(f"Fee structure matches budget ({advocate.fee_category})")
        else:
            score += 6
            reasons.append(f"Fee structure compatible ({advocate.fee_category})")
    else:
        score += 2  # Small points if at least they're an option
    
    # =================
    # LANGUAGE MATCH (5 points)
    # =================
    
    matching_languages = set(languages) & set(advocate.languages)
    
    if matching_languages:
        score += min(5, len(matching_languages) * 2)
        reasons.append(f"Speaks {', '.join(matching_languages)}")
    
    # =================
    # RATING BONUS (5 points)
    # =================
    
    if advocate.rating >= 4.5:
        score += 5
        reasons.append(f"Highly rated ({advocate.rating}/5, {advocate.total_reviews} reviews)")
    elif advocate.rating >= 4.0:
        score += 3
        reasons.append(f"Well rated ({advocate.rating}/5)")
    
    # =================
    # SUCCESS RATE BONUS
    # =================
    
    if advocate.success_rate_category == "excellent":
        score += 3
    elif advocate.success_rate_category == "good":
        score += 1
    
    return min(100.0, score), reasons


def execute_recommend_advocates_tool(tool_input: Dict[str, Any]) -> str:
    """
    Executes the recommend_advocates tool with the given input.
    
    This function:
    1. Validates the input parameters
    2. Filters advocates by hard requirements (geography, availability)
    3. Scores all eligible advocates
    4. Ranks and returns top recommendations with detailed explanations
    
    Returns:
        JSON string with ranked advocate recommendations
    """
    logger.info(f"Executing recommend_advocates tool with: {json.dumps(tool_input, indent=2)}")
    
    recommendations = []
    
    for adv_id, advocate in ADVOCATE_REGISTRY.items():
        score, reasons = calculate_advocate_match_score(advocate, tool_input)
        
        if score > 0:
            recommendations.append({
                "advocate_id": adv_id,
                "name": advocate.name,
                "enrollment_number": advocate.enrollment_number,
                "match_score": round(score, 1),
                "match_reasons": reasons,
                "years_of_practice": advocate.years_of_practice,
                "home_court": advocate.home_court,
                "specializations": advocate.specializations,
                "sub_specializations": advocate.sub_specializations,
                "fee_category": advocate.fee_category,
                "consultation_fee": advocate.consultation_fee,
                "languages": advocate.languages,
                "rating": advocate.rating,
                "total_reviews": advocate.total_reviews,
                "contact_phone": advocate.contact_phone,
                "contact_email": advocate.contact_email,
                "office_address": advocate.office_address,
                "current_availability": "High" if advocate.current_case_load < advocate.max_case_load * 0.6 else "Moderate"
            })
    
    # Sort by match score descending
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Take top 5 recommendations
    top_recommendations = recommendations[:5]
    
    result = {
        "status": "success",
        "search_criteria": {
            "matter_type": tool_input.get("matter_type"),
            "state": tool_input.get("state"),
            "district": tool_input.get("district"),
            "court_level": tool_input.get("court_level"),
            "complexity": tool_input.get("estimated_complexity", "moderate"),
            "budget": tool_input.get("budget_category", "standard")
        },
        "total_matches": len(recommendations),
        "recommendations": top_recommendations,
        "search_timestamp": datetime.now().isoformat()
    }
    
    if not top_recommendations:
        result["status"] = "no_matches"
        result["message"] = "No advocates found matching the specified criteria. Consider expanding search parameters."
    
    return json.dumps(result, indent=2, ensure_ascii=False)


# =============================================================================
# DATA STRUCTURES FOR SESSION MANAGEMENT
# =============================================================================

@dataclass
class ConversationSession:
    """Extended session to track the three-stage workflow."""
    user_id: int
    messages: List[Dict] = field(default_factory=list)
    container_id: Optional[str] = None
    
    # Workflow stage tracking
    current_stage: str = "none"  # "interview", "draft", "recommend", "none"
    current_workflow: Optional[str] = None
    document_type: Optional[str] = None
    
    # Case profile accumulated across stages
    case_profile: Optional[Dict] = None
    
    # Generated documents
    generated_documents: List[str] = field(default_factory=list)
    
    # Recommended advocates
    recommended_advocates: List[Dict] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)


user_sessions: Dict[int, ConversationSession] = {}

# =============================================================================
# ANTHROPIC CLIENT SETUP
# =============================================================================

client = None
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert Indian Advocate integrated with a professional advocate skill. Always read the advocate skill first.

## Three-Stage Workflow

You guide clients through a complete legal assistance journey:

### Stage 1: Client Interview
- Conduct structured fact-gathering following the advocate skill's interview phases
- Ask ONE question at a time and wait for responses
- Collect all material facts needed for document drafting
- Build a comprehensive case profile from the interview

### Stage 2: Legal Document Drafting
- Use the advocate skill to create professional legal documents
- Generate documents in .docx format following Indian court standards
- Maintain proper legal formatting and terminology

### Stage 3: Advocate Recommendation
- After completing interview and drafting, ALWAYS offer to recommend suitable advocates
- Use the recommend_advocates tool to find matching legal professionals
- Present recommendations with clear explanations of why each advocate is suitable

## Critical Instructions

1. When you generate a document file, inform the user and offer advocate recommendations
2. When using recommend_advocates, extract case characteristics from the conversation:
   - matter_type: civil, matrimonial, criminal, property, constitutional, conveyancing, notice
   - state and district from jurisdiction discussion
   - court_level from valuation and nature of case
   - estimated_complexity from case facts
   - budget_category if discussed

3. Present advocate recommendations in a clear, organized manner:
   - Show top 3-5 matches with match scores
   - Explain why each advocate is suitable
   - Include contact information for easy follow-up

4. Be professional but approachable, suitable for Telegram chat
5. Keep responses concise except when drafting legal documents

IMPORTANT: After completing document drafting, proactively suggest finding an advocate by saying something like:
"I've prepared your legal document. Would you like me to recommend suitable advocates who specialize in [matter type] cases in [jurisdiction]?"
"""

# =============================================================================
# HELPER FUNCTIONS (Same as original bot)
# =============================================================================

def log_response_structure(response, prefix: str = "") -> None:
    if not DEBUG_MODE:
        return
    logger.debug(f"{prefix}RESPONSE STRUCTURE - Stop: {response.stop_reason}")
    for i, block in enumerate(response.content):
        block_type = getattr(block, 'type', 'UNKNOWN')
        logger.debug(f"{prefix}Block [{i}] Type: {block_type}")


def extract_text_from_response(response) -> str:
    text_parts = []
    for block in response.content:
        if hasattr(block, 'text') and block.text:
            text_parts.append(block.text)
    return "\n".join(text_parts) if text_parts else "Request processed."


def extract_file_ids(response) -> List[Dict[str, str]]:
    files = []
    for block in response.content:
        block_type = getattr(block, 'type', None)
        
        if block_type == 'bash_code_execution_tool_result':
            content_item = getattr(block, 'content', None)
            if content_item:
                inner_type = getattr(content_item, 'type', None)
                if inner_type == 'bash_code_execution_result':
                    inner_content = getattr(content_item, 'content', [])
                    if isinstance(inner_content, list):
                        for file_item in inner_content:
                            file_id = getattr(file_item, 'file_id', None)
                            if file_id:
                                filename = getattr(file_item, 'filename', 'document.docx')
                                files.append({'file_id': file_id, 'filename': filename})
    
    return files


def extract_tool_use_blocks(response) -> List[Dict]:
    """Extract tool_use blocks from response for processing."""
    tool_blocks = []
    for block in response.content:
        if getattr(block, 'type', None) == 'tool_use':
            tool_blocks.append({
                'id': block.id,
                'name': block.name,
                'input': block.input
            })
    return tool_blocks


def serialize_content_for_history(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        serialized = []
        for block in content:
            block_type = getattr(block, 'type', None)
            if block_type == 'text':
                serialized.append({"type": "text", "text": getattr(block, 'text', '')})
            elif block_type == 'tool_use':
                serialized.append({
                    "type": "tool_use",
                    "id": getattr(block, 'id', ''),
                    "name": getattr(block, 'name', ''),
                    "input": getattr(block, 'input', {})
                })
        return serialized if serialized else content
    if hasattr(content, 'content'):
        return serialize_content_for_history(content.content)
    return content


async def download_file(file_id: str) -> tuple:
    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            metadata = client.beta.files.retrieve_metadata(
                file_id=file_id, betas=["files-api-2025-04-14"])
            if not metadata.downloadable:
                return None, metadata
            content = client.beta.files.download(
                file_id=file_id, betas=["files-api-2025-04-14"])
            return content, metadata
        except anthropic.NotFoundError:
            return None, None
        except anthropic.APIError as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)
            else:
                return None, None
    return None, None


# =============================================================================
# ENHANCED CLAUDE API WITH CUSTOM TOOL SUPPORT
# =============================================================================

async def get_claude_response_with_tools(user_id: int, user_message: str, file_data: Optional[List[Dict]] = None) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Send a message to Claude with both the advocate skill and custom tools.

    This function integrates:
    1. The advocate-skill for interviews and document drafting
    2. The recommend_advocates custom tool for matching

    Args:
        user_id: Telegram user ID
        user_message: Text message from user
        file_data: Optional list of file dictionaries with 'media_type', 'data', 'filename'

    Returns:
        Tuple of (text_response, list_of_files, list_of_advocate_recommendations)
    """
    if client is None:
        return "⚠️ API not configured. Please set ANTHROPIC_API_KEY.", [], []

    # Session management
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationSession(user_id=user_id)

    session = user_sessions[user_id]
    session.last_activity = datetime.now()

    # Build content blocks (files first, then text)
    content_blocks = []

    # Supported image types
    SUPPORTED_IMAGE_TYPES = {
        'image/jpeg': 'image/jpeg',
        'image/png': 'image/png',
        'image/gif': 'image/gif',
        'image/webp': 'image/webp'
    }

    # Add files if provided
    if file_data:
        for file_info in file_data:
            media_type = file_info.get('media_type', '')
            data = file_info.get('data', '')
            filename = file_info.get('filename', 'uploaded_file')

            if media_type == 'application/pdf':
                content_blocks.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": data
                    },
                    "title": filename
                })
                logger.info(f"Added PDF document: {filename}")

            elif media_type in SUPPORTED_IMAGE_TYPES:
                content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": SUPPORTED_IMAGE_TYPES.get(media_type, media_type),
                        "data": data
                    }
                })
                logger.info(f"Added image: {filename}")

    # Add text message
    if user_message and user_message.strip():
        content_blocks.append({"type": "text", "text": user_message})
    elif file_data:
        content_blocks.append({
            "type": "text",
            "text": "Please see this document/image."
        })

    session.messages.append({"role": "user", "content": content_blocks})
    
    if len(session.messages) > MAX_HISTORY_MESSAGES:
        session.messages = session.messages[-MAX_HISTORY_MESSAGES:]
    
    try:
        # Define custom tools alongside skill-provided tools
        custom_tools = [
            {
                "type": "code_execution_20250825",
                "name": "code_execution"
            },
            recommend_advocates_tool_schema()  # Our custom tool
        ]
        
        container_config = {
            "skills": [{
                "type": "custom",
                "skill_id": ADVOCATE_SKILL_ID,
                "version": "latest"
            }]
        }
        
        if session.container_id:
            container_config["id"] = session.container_id
        
        logger.info(f"Sending message to Claude (container: {session.container_id or 'new'})")
        
        response = client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=8192,
            betas=SKILLS_BETAS,
            system=SYSTEM_PROMPT,
            container=container_config,
            messages=session.messages,
            tools=custom_tools
        )
        
        if hasattr(response, 'container') and response.container:
            session.container_id = response.container.id
        
        # Handle pause_turn for long-running operations
        retry_count = 0
        while response.stop_reason == "pause_turn" and retry_count < MAX_PAUSE_RETRIES:
            retry_count += 1
            session.messages.append({
                "role": "assistant",
                "content": serialize_content_for_history(response.content)
            })
            response = client.beta.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=8192,
                betas=SKILLS_BETAS,
                system=SYSTEM_PROMPT,
                container={"id": session.container_id, "skills": [{"type": "custom", "skill_id": ADVOCATE_SKILL_ID, "version": "latest"}]},
                messages=session.messages,
                tools=custom_tools
            )
        
        # Process tool use if Claude requested our custom tool
        advocate_recommendations = []
        tool_blocks = extract_tool_use_blocks(response)
        
        for tool_block in tool_blocks:
            if tool_block['name'] == 'recommend_advocates':
                logger.info(f"Processing recommend_advocates tool call")
                
                # Execute our custom tool
                tool_result = execute_recommend_advocates_tool(tool_block['input'])
                
                # Parse and store recommendations
                result_data = json.loads(tool_result)
                if result_data.get('status') == 'success':
                    advocate_recommendations = result_data.get('recommendations', [])
                    session.recommended_advocates = advocate_recommendations
                
                # Send tool result back to Claude for natural language response
                session.messages.append({
                    "role": "assistant",
                    "content": serialize_content_for_history(response.content)
                })
                session.messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_block['id'],
                        "content": tool_result
                    }]
                })
                
                # Get Claude's interpretation of the results
                response = client.beta.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=8192,
                    betas=SKILLS_BETAS,
                    system=SYSTEM_PROMPT,
                    container={"id": session.container_id, "skills": [{"type": "custom", "skill_id": ADVOCATE_SKILL_ID, "version": "latest"}]},
                    messages=session.messages,
                    tools=custom_tools
                )
        
        text_response = extract_text_from_response(response)
        files = extract_file_ids(response)
        
        session.messages.append({"role": "assistant", "content": text_response})
        
        return text_response, files, advocate_recommendations
        
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return f"⚠️ API Error: {str(e)}", [], []
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return "⚠️ An unexpected error occurred. Use /reset to start fresh.", [], []


# =============================================================================
# TELEGRAM HANDLERS
# =============================================================================

async def send_generated_files(update: Update, files: List[Dict]) -> None:
    """Download and send generated files to user."""
    for file_info in files:
        file_id = file_info['file_id']
        expected_filename = file_info.get('filename', 'document.docx')
        
        try:
            content, metadata = await download_file(file_id)
            if content is None:
                await update.message.reply_text(f"⚠️ Could not download: {expected_filename}")
                continue
            
            filename = metadata.filename if metadata else expected_filename
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
                if isinstance(content, bytes):
                    tmp.write(content)
                elif hasattr(content, 'write_to_file'):
                    content.write_to_file(tmp.name)
                elif hasattr(content, 'read'):
                    tmp.write(content.read())
                else:
                    tmp.write(content)
                tmp_path = tmp.name
            
            with open(tmp_path, 'rb') as doc_file:
                await update.message.reply_document(
                    document=InputFile(doc_file, filename=filename),
                    caption=f"📄 Generated: {filename}"
                )
            
            os.unlink(tmp_path)
            
        except Exception as e:
            logger.error(f"Error sending file: {e}", exc_info=True)
            await update.message.reply_text(f"⚠️ Error sending document: {str(e)}")


def format_advocate_recommendations(recommendations: List[Dict]) -> str:
    """Format advocate recommendations for Telegram display."""
    if not recommendations:
        return "No matching advocates found."
    
    formatted = ["🏛️ **Recommended Advocates**\n"]
    
    for i, adv in enumerate(recommendations[:5], 1):
        formatted.append(f"\n**{i}. {adv['name']}**")
        formatted.append(f"📊 Match Score: {adv['match_score']}/100")
        formatted.append(f"⚖️ {adv['years_of_practice']} years | {adv['home_court']}")
        formatted.append(f"💼 {', '.join(adv['specializations'][:3])}")
        formatted.append(f"⭐ {adv['rating']}/5 ({adv['total_reviews']} reviews)")
        formatted.append(f"💰 {adv['fee_category'].title()} | Consult: ₹{adv['consultation_fee'] or 'Free'}")
        formatted.append(f"📞 {adv['contact_phone']}")
        formatted.append(f"✉️ {adv['contact_email']}")
        
        if adv.get('match_reasons'):
            formatted.append(f"✅ " + " | ".join(adv['match_reasons'][:3]))
    
    return "\n".join(formatted)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
    user_sessions[user_id] = ConversationSession(user_id=user_id)
    
    welcome_message = f"""🏛️ **Advocate ROSS - Complete Legal Assistant**

Hello {user.first_name}! I guide you through your complete legal journey:

**📋 Stage 1: Client Interview**
Systematic fact-gathering for your legal matter

**📝 Stage 2: Document Drafting**
Professional legal documents in Indian court format

**👨‍⚖️ Stage 3: Advocate Matching**
Find the right lawyer for your case

━━━━━━━━━━━━━━━━━━━━━━
Select an option to begin:"""

    keyboard = [
        [InlineKeyboardButton("📋 Start Interview", callback_data="workflow_interview")],
        [InlineKeyboardButton("📝 Create Document", callback_data="workflow_draft")],
        [InlineKeyboardButton("👨‍⚖️ Find Advocate", callback_data="workflow_recommend")],
        [InlineKeyboardButton("📚 Document Types", callback_data="show_documents")],
    ]
    
    await update.message.reply_text(
        welcome_message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /recommend command for direct advocate search."""
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationSession(user_id=user_id)
    
    session = user_sessions[user_id]
    session.current_stage = "recommend"
    
    keyboard = [
        [
            InlineKeyboardButton("⚖️ Civil", callback_data="rec_civil"),
            InlineKeyboardButton("💑 Matrimonial", callback_data="rec_matrimonial"),
        ],
        [
            InlineKeyboardButton("🔓 Criminal", callback_data="rec_criminal"),
            InlineKeyboardButton("🏠 Property", callback_data="rec_property"),
        ],
        [
            InlineKeyboardButton("📜 Constitutional", callback_data="rec_constitutional"),
        ],
    ]
    
    await update.message.reply_text(
        "👨‍⚖️ **Find an Advocate**\n\n"
        "I'll help you find the right advocate for your case.\n"
        "First, what type of legal matter is this?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """🏛️ **Complete Legal Assistant - Help**

**Three-Stage Workflow:**

**Stage 1: Interview** `/interview`
Structured fact-gathering for your case

**Stage 2: Draft** `/draft`
Generate professional legal documents

**Stage 3: Recommend** `/recommend`
Find suitable advocates for your case

**Other Commands:**
• `/start` - Main menu
• `/generate <request>` - Quick document
• `/documents` - List document types
• `/reset` - Clear session
• `/debug` - Toggle debug mode

**Tips:**
• Complete the interview for best advocate matches
• Answer questions one at a time
• Upload PDFs or images if you have documents

⚠️ *All documents should be reviewed by a qualified advocate before filing.*"""

    await update.message.reply_text(help_text, parse_mode="Markdown")


async def interview_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationSession(user_id=user_id)
    
    session = user_sessions[user_id]
    session.current_stage = "interview"
    session.current_workflow = "interview"
    
    keyboard = [
        [
            InlineKeyboardButton("⚖️ Civil Suit", callback_data="interview_civil"),
            InlineKeyboardButton("💑 Matrimonial", callback_data="interview_matrimonial"),
        ],
        [
            InlineKeyboardButton("🔓 Bail Application", callback_data="interview_bail"),
            InlineKeyboardButton("🏠 Property Matter", callback_data="interview_property"),
        ],
        [InlineKeyboardButton("📜 Other", callback_data="interview_other")],
    ]
    
    await update.message.reply_text(
        "📋 **Client Interview Mode**\n\n"
        "I'll gather all the facts needed for your legal matter.\n"
        "Select the type of matter:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def draft_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationSession(user_id=user_id)
    
    session = user_sessions[user_id]
    session.current_stage = "draft"
    session.current_workflow = "draft"
    
    keyboard = [
        [
            InlineKeyboardButton("📄 Civil", callback_data="draft_civil"),
            InlineKeyboardButton("💔 Matrimonial", callback_data="draft_matrimonial"),
        ],
        [
            InlineKeyboardButton("⚖️ Constitutional", callback_data="draft_constitutional"),
            InlineKeyboardButton("🚔 Criminal", callback_data="draft_criminal"),
        ],
        [
            InlineKeyboardButton("🏠 Conveyancing", callback_data="draft_conveyancing"),
            InlineKeyboardButton("📬 Notice", callback_data="draft_notice"),
        ],
    ]
    
    await update.message.reply_text(
        "📝 **Document Drafting**\n\nSelect document category:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def documents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """📚 **Available Document Types**

**Civil:** Plaints, Written Statements, Injunctions
**Matrimonial:** Divorce, Restitution, Maintenance
**Constitutional:** Writs, PILs, SLPs
**Criminal:** Bail Applications, Section 138
**Conveyancing:** Sale Deeds, Wills, POA
**Notices:** Section 80, 106, 138

Use /draft to create documents!
Use /recommend to find advocates!"""
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if context.args:
        document_request = " ".join(context.args)
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        processing_msg = await update.message.reply_text(
            "📄 **Generating document...**\n\nThis may take a moment.",
            parse_mode="Markdown"
        )
        
        prompt = f"""Please generate a professional legal document based on this request: {document_request}

Use the advocate skill to create a properly formatted document following Indian legal standards.
Generate the document as a .docx file.

After generating the document, use the recommend_advocates tool to suggest suitable advocates who could help with this type of matter."""
        
        response_text, files, recommendations = await get_claude_response_with_tools(user_id, prompt)
        
        await processing_msg.delete()
        
        # Send response
        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                try:
                    await update.message.reply_text(response_text[i:i+4000], parse_mode="Markdown")
                except:
                    await update.message.reply_text(response_text[i:i+4000])
        else:
            try:
                await update.message.reply_text(response_text, parse_mode="Markdown")
            except:
                await update.message.reply_text(response_text)
        
        if files:
            await send_generated_files(update, files)
        
        # Send recommendations if available
        if recommendations:
            rec_text = format_advocate_recommendations(recommendations)
            try:
                await update.message.reply_text(rec_text, parse_mode="Markdown")
            except:
                await update.message.reply_text(rec_text)
    else:
        await update.message.reply_text(
            "📝 **Document Generation**\n\n"
            "Usage: `/generate <document request>`\n\n"
            "**Examples:**\n"
            "• `/generate sale deed for agricultural land`\n"
            "• `/generate bail application for theft case`\n"
            "• `/generate section 138 legal notice`",
            parse_mode="Markdown"
        )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await update.message.reply_text(
        "🔄 **Session Reset**\n\nUse /start to begin fresh.",
        parse_mode="Markdown"
    )


async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global DEBUG_MODE
    DEBUG_MODE = not DEBUG_MODE
    
    status = "enabled" if DEBUG_MODE else "disabled"
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    await update.message.reply_text(
        f"🔧 Debug mode **{status}**",
        parse_mode="Markdown"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in user_sessions:
        user_sessions[user_id] = ConversationSession(user_id=user_id)
    
    session = user_sessions[user_id]
    
    # Handle workflow selection
    if data == "workflow_interview":
        session.current_stage = "interview"
        keyboard = [
            [
                InlineKeyboardButton("⚖️ Civil", callback_data="interview_civil"),
                InlineKeyboardButton("💑 Matrimonial", callback_data="interview_matrimonial"),
            ],
            [
                InlineKeyboardButton("🔓 Bail", callback_data="interview_bail"),
                InlineKeyboardButton("🏠 Property", callback_data="interview_property"),
            ],
        ]
        await query.edit_message_text(
            "📋 **Interview Mode**\n\nSelect matter type:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data == "workflow_draft":
        session.current_stage = "draft"
        keyboard = [
            [
                InlineKeyboardButton("📄 Civil", callback_data="draft_civil"),
                InlineKeyboardButton("💔 Matrimonial", callback_data="draft_matrimonial"),
            ],
            [
                InlineKeyboardButton("⚖️ Constitutional", callback_data="draft_constitutional"),
                InlineKeyboardButton("🚔 Criminal", callback_data="draft_criminal"),
            ],
            [
                InlineKeyboardButton("🏠 Conveyancing", callback_data="draft_conveyancing"),
                InlineKeyboardButton("📬 Notice", callback_data="draft_notice"),
            ],
        ]
        await query.edit_message_text(
            "📝 **Drafting Mode**\n\nSelect document type:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data == "workflow_recommend":
        session.current_stage = "recommend"
        keyboard = [
            [
                InlineKeyboardButton("⚖️ Civil", callback_data="rec_civil"),
                InlineKeyboardButton("💑 Matrimonial", callback_data="rec_matrimonial"),
            ],
            [
                InlineKeyboardButton("🔓 Criminal", callback_data="rec_criminal"),
                InlineKeyboardButton("🏠 Property", callback_data="rec_property"),
            ],
        ]
        await query.edit_message_text(
            "👨‍⚖️ **Find an Advocate**\n\nWhat type of matter?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    elif data == "show_documents":
        await query.edit_message_text(
            "📚 **Document Categories**\n\n"
            "• Civil - Plaints, Injunctions\n"
            "• Matrimonial - Divorce, Maintenance\n"
            "• Constitutional - Writs, PILs\n"
            "• Criminal - Bail, Section 138\n"
            "• Conveyancing - Deeds, Wills\n"
            "• Notices - Sec 80, 106, 138\n\n"
            "Use /draft to create documents!\n"
            "Use /recommend to find advocates!",
            parse_mode="Markdown"
        )
        
    # Handle interview callbacks
    elif data.startswith("interview_"):
        matter_type = data.replace("interview_", "")
        session.document_type = matter_type
        session.case_profile = {"matter_type": matter_type}
        
        await query.edit_message_text("⏳ Starting interview...")
        response, files, _ = await get_claude_response_with_tools(
            user_id,
            f"I need help with a {matter_type} matter. Please begin the client interview by asking the first question."
        )
        try:
            await query.message.reply_text(response, parse_mode="Markdown")
        except:
            await query.message.reply_text(response)
        
    # Handle draft callbacks
    elif data.startswith("draft_"):
        doc_type = data.replace("draft_", "")
        session.document_type = doc_type
        
        type_names = {
            "civil": "civil pleading",
            "matrimonial": "matrimonial petition",
            "constitutional": "constitutional petition",
            "criminal": "criminal application",
            "conveyancing": "conveyancing document",
            "notice": "legal notice"
        }
        
        await query.edit_message_text(
            f"📝 **{type_names.get(doc_type, doc_type).title()} Drafting**\n\n"
            "Please describe:\n"
            "1. The specific document you need\n"
            "2. Brief facts of the case\n"
            "3. Jurisdiction (state/district)\n"
            "4. Any budget preferences for advocate",
            parse_mode="Markdown"
        )
        
    # Handle recommend callbacks
    elif data.startswith("rec_"):
        matter_type = data.replace("rec_", "")
        session.case_profile = {"matter_type": matter_type}
        
        await query.edit_message_text(
            f"👨‍⚖️ **Finding {matter_type.title()} Advocates**\n\n"
            "To find the best match, please tell me:\n"
            "1. Which state and district?\n"
            "2. Brief description of your case\n"
            "3. Budget preference (premium/standard/affordable)\n"
            "4. Any language preferences",
            parse_mode="Markdown"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages through the three-stage workflow."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    response_text, files, recommendations = await get_claude_response_with_tools(user_id, user_message)
    
    # Send text response
    if len(response_text) > 4000:
        for i in range(0, len(response_text), 4000):
            try:
                await update.message.reply_text(response_text[i:i+4000], parse_mode="Markdown")
            except:
                await update.message.reply_text(response_text[i:i+4000])
    else:
        try:
            await update.message.reply_text(response_text, parse_mode="Markdown")
        except:
            await update.message.reply_text(response_text)
    
    # Send files if any
    if files:
        await send_generated_files(update, files)
    
    # Send formatted recommendations if Claude used the tool
    if recommendations:
        rec_text = format_advocate_recommendations(recommendations)
        try:
            await update.message.reply_text(rec_text, parse_mode="Markdown")
        except:
            await update.message.reply_text(rec_text)


async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle PDF uploads."""
    user_id = update.effective_user.id
    document = update.message.document

    MAX_FILE_SIZE = 20 * 1024 * 1024
    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("⚠️ File too large (max 20MB)")
        return

    mime_type = document.mime_type or ""
    filename = document.file_name or "document.pdf"

    if mime_type != "application/pdf":
        await update.message.reply_text("⚠️ Only PDF files supported for upload")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    processing_msg = await update.message.reply_text(f"📄 Processing `{filename}`...", parse_mode="Markdown")

    try:
        # Download PDF from Telegram
        tg_file = await document.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        file_base64 = base64.standard_b64encode(bytes(file_bytes)).decode("utf-8")

        # Get user's caption or use default
        user_message = update.message.caption or "Please review this document."

        # Prepare file data for Claude
        file_data = [{
            'media_type': 'application/pdf',
            'data': file_base64,
            'filename': filename
        }]

        # Send to Claude with actual PDF data
        response_text, files, recommendations = await get_claude_response_with_tools(
            user_id,
            user_message,
            file_data=file_data
        )

        await processing_msg.delete()

        # Send response
        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                await update.message.reply_text(response_text[i:i+4000])
        else:
            try:
                await update.message.reply_text(response_text, parse_mode="Markdown")
            except:
                await update.message.reply_text(response_text)

        if files:
            await send_generated_files(update, files)

        if recommendations:
            rec_text = format_advocate_recommendations(recommendations)
            await update.message.reply_text(rec_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        await processing_msg.delete()
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo uploads."""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]  # Get highest resolution

    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB limit for images
    if photo.file_size and photo.file_size > MAX_IMAGE_SIZE:
        await update.message.reply_text("⚠️ Image too large (max 5MB)")
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    processing_msg = await update.message.reply_text("🖼️ Processing image...")

    try:
        # Download image from Telegram
        tg_file = await photo.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        file_base64 = base64.standard_b64encode(bytes(file_bytes)).decode("utf-8")

        # Determine image format
        file_path = tg_file.file_path or ""
        if file_path.lower().endswith('.png'):
            media_type = 'image/png'
        elif file_path.lower().endswith('.gif'):
            media_type = 'image/gif'
        elif file_path.lower().endswith('.webp'):
            media_type = 'image/webp'
        else:
            media_type = 'image/jpeg'  # Default to JPEG

        # Get user's caption or use default
        user_message = update.message.caption or "Please analyze this image."

        # Prepare image data for Claude
        file_data = [{
            'media_type': media_type,
            'data': file_base64,
            'filename': f'image.{media_type.split("/")[1]}'
        }]

        # Send to Claude with actual image data
        response_text, files, recommendations = await get_claude_response_with_tools(
            user_id,
            user_message,
            file_data=file_data
        )

        await processing_msg.delete()

        try:
            await update.message.reply_text(response_text, parse_mode="Markdown")
        except:
            await update.message.reply_text(response_text)

        if files:
            await send_generated_files(update, files)

        if recommendations:
            rec_text = format_advocate_recommendations(recommendations)
            await update.message.reply_text(rec_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Photo upload error: {e}", exc_info=True)
        await processing_msg.delete()
        await update.message.reply_text(f"⚠️ Error: {str(e)}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Try again or use /reset."
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Start the bot with full three-stage workflow."""
    logger.info("Starting Complete Legal Assistant Bot...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set!")
        return
    
    logger.info(f"Debug mode: {DEBUG_MODE}")
    logger.info(f"Skill ID: {ADVOCATE_SKILL_ID}")
    logger.info(f"Advocate Registry: {len(ADVOCATE_REGISTRY)} advocates loaded")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("interview", interview_command))
    application.add_handler(CommandHandler("draft", draft_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("documents", documents_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("debug", debug_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # File handlers
    application.add_handler(MessageHandler(
        filters.Document.MimeType("application/pdf"),
        handle_document_upload
    ))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_upload))
    
    # Text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Errors
    application.add_error_handler(error_handler)
    
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
