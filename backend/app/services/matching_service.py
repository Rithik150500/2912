"""
Advocate Matching Service
Implements intelligent matching between cases and advocates based on multiple criteria.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.advocate_profile import AdvocateProfile
from app.models.user import User

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for matching cases with suitable advocates."""

    async def get_recommendations(
        self,
        db: AsyncSession,
        case_profile: Dict[str, Any],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get advocate recommendations based on case profile.

        Args:
            db: Database session
            case_profile: Dictionary with case details
            limit: Maximum number of recommendations

        Returns:
            List of recommended advocates with match scores
        """
        # Fetch all available advocates with their user profiles
        result = await db.execute(
            select(AdvocateProfile, User)
            .join(User, AdvocateProfile.user_id == User.id)
            .where(AdvocateProfile.is_available == True)
            .where(User.is_active == True)
        )
        advocates = result.all()

        recommendations = []

        for advocate_profile, user in advocates:
            score, reasons = self._calculate_match_score(advocate_profile, user, case_profile)

            if score > 0:
                recommendations.append({
                    "advocate_id": str(user.id),
                    "profile_id": str(advocate_profile.id),
                    "name": user.full_name,
                    "email": user.email,
                    "phone": user.phone,
                    "enrollment_number": advocate_profile.enrollment_number,
                    "match_score": round(score, 1),
                    "match_reasons": reasons,
                    "years_of_practice": advocate_profile.experience_years,
                    "home_court": advocate_profile.home_court,
                    "specializations": advocate_profile.primary_specializations or [],
                    "sub_specializations": advocate_profile.sub_specializations or [],
                    "fee_category": advocate_profile.fee_category.value if advocate_profile.fee_category else "standard",
                    "consultation_fee": float(advocate_profile.consultation_fee) if advocate_profile.consultation_fee else None,
                    "languages": advocate_profile.languages or [],
                    "rating": float(advocate_profile.rating) if advocate_profile.rating else 0.0,
                    "review_count": advocate_profile.review_count,
                    "office_address": advocate_profile.office_address,
                    "is_verified": advocate_profile.is_verified,
                    "current_availability": self._get_availability_status(advocate_profile)
                })

        # Sort by match score descending
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)

        return recommendations[:limit]

    def _calculate_match_score(
        self,
        profile: AdvocateProfile,
        user: User,
        case_profile: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """
        Calculate match score between an advocate and a case profile.

        Scoring breakdown:
        - Specialization match: 30 points max
        - Geographic match: 25 points max (also a hard filter)
        - Experience alignment: 15 points max
        - Availability: 10 points max
        - Fee alignment: 10 points max
        - Language match: 5 points max
        - Rating bonus: 5 points max

        Returns:
            Tuple of (score 0.0-100.0, list of match reasons)
        """
        score = 0.0
        reasons = []

        # Extract case parameters with defaults
        matter_type = case_profile.get("matter_type", "")
        sub_category = case_profile.get("sub_category", "")
        state = case_profile.get("state", "")
        district = case_profile.get("district", "")
        court_level = case_profile.get("court_level", "district")
        complexity = case_profile.get("complexity", case_profile.get("estimated_complexity", "moderate"))
        urgency = case_profile.get("urgency", case_profile.get("urgency_level", "normal"))
        languages = case_profile.get("preferred_languages", ["Hindi", "English"])
        budget = case_profile.get("budget_category", "standard")
        specific_expertise = case_profile.get("specific_expertise_needed", [])

        advocate_states = profile.states or []
        advocate_districts = profile.districts or []
        advocate_specializations = profile.primary_specializations or []
        advocate_sub_specs = profile.sub_specializations or []
        advocate_languages = profile.languages or []

        # =================
        # HARD FILTERS
        # =================

        # Geographic availability is a must
        if state and advocate_states and state not in advocate_states:
            return 0.0, [f"Not available in {state}"]

        # Must be available for new cases
        if not profile.is_available:
            return 0.0, ["Currently not accepting new cases"]

        # =================
        # SPECIALIZATION MATCH (30 points)
        # =================

        if matter_type and matter_type in advocate_specializations:
            score += 20
            reasons.append(f"Specializes in {matter_type} matters")

            # Bonus for exact sub-specialization match
            if specific_expertise:
                for expertise in specific_expertise:
                    if any(expertise.lower() in sub.lower() for sub in advocate_sub_specs):
                        score += 5
                        reasons.append(f"Expert in {expertise}")
                        break

            # Sub-category alignment
            if sub_category:
                for sub in advocate_sub_specs:
                    if sub_category.lower() in sub.lower() or sub.lower() in sub_category.lower():
                        score += 5
                        reasons.append(f"Handles {sub_category} cases regularly")
                        break
        elif specific_expertise:
            # Partial match if sub-specializations align
            for expertise in specific_expertise:
                if any(expertise.lower() in sub.lower() for sub in advocate_sub_specs):
                    score += 10
                    reasons.append(f"Has experience with {expertise}")
                    break

        # =================
        # GEOGRAPHIC MATCH (25 points)
        # =================

        if state in advocate_states:
            score += 10
            reasons.append(f"Practices in {state}")

        # District familiarity bonus
        if district and district in advocate_districts:
            score += 10
            reasons.append(f"Familiar with {district} courts")

        # Home court bonus for high court cases
        if court_level == "high_court" and profile.home_court:
            if state.lower() in profile.home_court.lower():
                score += 5
                reasons.append(f"Home court is {profile.home_court}")

        # =================
        # EXPERIENCE ALIGNMENT (15 points)
        # =================

        complexity_requirements = {
            "simple": 3,
            "moderate": 5,
            "complex": 10,
            "highly_complex": 15
        }

        min_years = complexity_requirements.get(complexity, 5)
        years = profile.experience_years or 0

        if years >= min_years:
            experience_score = min(15, 8 + (years - min_years) * 0.5)
            score += experience_score
            reasons.append(f"{years} years of practice")
        else:
            score += 5

        # Court level experience
        if court_level == "high_court" and profile.landmark_cases:
            landmark_count = len(profile.landmark_cases.split(',')) if isinstance(profile.landmark_cases, str) else 0
            if landmark_count > 5:
                score += 3
                reasons.append("Experience with High Court matters")

        # =================
        # AVAILABILITY (10 points)
        # =================

        max_capacity = profile.max_case_capacity or 20
        current_load = profile.current_case_load or 0
        workload_ratio = current_load / max_capacity if max_capacity > 0 else 0

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
                score -= 5

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
        advocate_fee = profile.fee_category.value if profile.fee_category else "standard"

        if advocate_fee in acceptable_fees:
            if advocate_fee == budget:
                score += 10
                reasons.append(f"Fee structure matches budget ({advocate_fee})")
            else:
                score += 6
                reasons.append(f"Fee structure compatible ({advocate_fee})")
        else:
            score += 2

        # =================
        # LANGUAGE MATCH (5 points)
        # =================

        matching_languages = set(languages or []) & set(advocate_languages)

        if matching_languages:
            score += min(5, len(matching_languages) * 2)
            reasons.append(f"Speaks {', '.join(matching_languages)}")

        # =================
        # RATING BONUS (5 points)
        # =================

        rating = float(profile.rating) if profile.rating else 0

        if rating >= 4.5:
            score += 5
            reasons.append(f"Highly rated ({rating}/5, {profile.review_count} reviews)")
        elif rating >= 4.0:
            score += 3
            reasons.append(f"Well rated ({rating}/5)")

        # =================
        # SUCCESS RATE BONUS
        # =================

        if profile.success_rate:
            success_rate = float(profile.success_rate)
            if success_rate >= 80:
                score += 3
            elif success_rate >= 60:
                score += 1

        return min(100.0, score), reasons

    def _get_availability_status(self, profile: AdvocateProfile) -> str:
        """Get human-readable availability status."""
        max_capacity = profile.max_case_capacity or 20
        current_load = profile.current_case_load or 0
        ratio = current_load / max_capacity if max_capacity > 0 else 0

        if ratio < 0.5:
            return "High"
        elif ratio < 0.8:
            return "Moderate"
        else:
            return "Limited"

    async def get_advocate_by_id(
        self,
        db: AsyncSession,
        advocate_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get advocate details by user ID."""
        result = await db.execute(
            select(AdvocateProfile, User)
            .join(User, AdvocateProfile.user_id == User.id)
            .where(User.id == advocate_id)
        )
        row = result.first()

        if not row:
            return None

        profile, user = row

        return {
            "advocate_id": str(user.id),
            "profile_id": str(profile.id),
            "name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "enrollment_number": profile.enrollment_number,
            "years_of_practice": profile.experience_years,
            "home_court": profile.home_court,
            "specializations": profile.primary_specializations or [],
            "sub_specializations": profile.sub_specializations or [],
            "fee_category": profile.fee_category.value if profile.fee_category else "standard",
            "consultation_fee": float(profile.consultation_fee) if profile.consultation_fee else None,
            "languages": profile.languages or [],
            "rating": float(profile.rating) if profile.rating else 0.0,
            "review_count": profile.review_count,
            "office_address": profile.office_address,
            "is_verified": profile.is_verified,
            "is_available": profile.is_available,
            "current_availability": self._get_availability_status(profile)
        }


# Global instance
matching_service = MatchingService()
