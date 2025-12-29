"""
AI Service - Claude Integration for Legal Assistant
Handles AI-powered conversations, case analysis, and document generation.
"""

import json
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

import anthropic
from app.config import settings

logger = logging.getLogger(__name__)

# System prompt for Claude
SYSTEM_PROMPT = """You are an expert Indian Advocate integrated with a professional advocate skill.

## Three-Stage Workflow

You guide clients through a complete legal assistance journey:

### Stage 1: Client Interview
- Conduct structured fact-gathering following proper legal interview methodology
- Ask ONE question at a time and wait for responses
- Collect all material facts needed for document drafting
- Build a comprehensive case profile from the interview
- Cover: parties involved, dates, jurisdiction, facts, relief sought

### Stage 2: Legal Document Drafting
- Create professional legal documents following Indian court standards
- Generate documents in proper legal format
- Maintain proper legal formatting and terminology

### Stage 3: Advocate Recommendation
- After completing interview and drafting, ALWAYS offer to recommend suitable advocates
- Use the recommend_advocates tool to find matching legal professionals
- Present recommendations with clear explanations of why each advocate is suitable

## Interview Guidelines

For each matter type, gather these essential facts:

**Civil Matters**: Parties, cause of action, jurisdiction, relief sought, limitation period
**Matrimonial**: Marriage details, grounds for relief, children, assets, maintenance claims
**Criminal/Bail**: Offense details, arrest circumstances, prior record, grounds for bail
**Property**: Property details, ownership chain, dispute nature, documents available
**Constitutional**: Fundamental right violated, state action, urgency

## Critical Instructions

1. Be systematic - ask one question at a time
2. Extract case profile details during interview:
   - matter_type: civil, matrimonial, criminal, property, constitutional, conveyancing, notice
   - state and district from jurisdiction discussion
   - court_level from valuation and nature of case
   - estimated_complexity from case facts
   - budget_category if discussed

3. After gathering sufficient facts, offer to:
   - Draft relevant legal documents
   - Recommend suitable advocates

4. Be professional but approachable
5. Keep responses concise and focused

When you have gathered enough information to create a case profile, include this JSON block in your response:
```case_profile
{
  "matter_type": "...",
  "sub_category": "...",
  "state": "...",
  "district": "...",
  "court_level": "...",
  "complexity": "...",
  "case_summary": "..."
}
```
"""

RECOMMEND_ADVOCATES_TOOL = {
    "name": "recommend_advocates",
    "description": """Recommends suitable advocates for a legal matter based on case characteristics.

This tool should be used AFTER completing the client interview. It matches the case profile
against the advocate registry to find the most suitable legal professionals based on:

1. SPECIALIZATION MATCH: Advocate's practice areas vs case matter type
2. GEOGRAPHIC AVAILABILITY: Where the advocate can appear vs where case will be filed
3. EXPERIENCE LEVEL: Years of practice and case complexity requirements
4. CAPACITY: Current workload and availability for new cases
5. FEE STRUCTURE: Client's budget vs advocate's fee category
6. LANGUAGE: Client's preferred languages vs advocate's working languages""",

    "input_schema": {
        "type": "object",
        "properties": {
            "matter_type": {
                "type": "string",
                "enum": ["civil", "matrimonial", "criminal", "property", "constitutional", "conveyancing", "notice"],
                "description": "Primary type of legal matter."
            },
            "sub_category": {
                "type": "string",
                "description": "Specific type of document or legal issue."
            },
            "state": {
                "type": "string",
                "description": "Indian state where the case will be filed."
            },
            "district": {
                "type": "string",
                "description": "District where the case will be filed."
            },
            "court_level": {
                "type": "string",
                "enum": ["district", "high_court", "supreme_court", "tribunal"],
                "description": "Level of court where case will be filed."
            },
            "estimated_complexity": {
                "type": "string",
                "enum": ["simple", "moderate", "complex", "highly_complex"],
                "description": "Estimated complexity based on facts."
            },
            "preferred_languages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Languages the client is comfortable with."
            },
            "budget_category": {
                "type": "string",
                "enum": ["premium", "standard", "affordable", "pro_bono"],
                "description": "Client's budget constraints."
            }
        },
        "required": ["matter_type", "state", "district", "court_level"]
    }
}


class AIService:
    """Service for handling AI conversations using Claude."""

    def __init__(self):
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    async def process_message(
        self,
        message: str,
        conversation_history: List[Dict[str, Any]],
        container_id: Optional[str] = None
    ) -> Tuple[str, Optional[str], Optional[Dict], bool]:
        """
        Process a user message and get AI response.

        Args:
            message: User's message
            conversation_history: Previous messages in the conversation
            container_id: Claude container ID for state persistence

        Returns:
            Tuple of (response_text, new_container_id, extracted_case_profile, tool_used)
        """
        if not self.client:
            return "AI service not configured. Please set ANTHROPIC_API_KEY.", None, None, False

        # Build messages for Claude
        messages = self._build_messages(conversation_history, message)

        try:
            # Make API call with tools
            response = await asyncio.to_thread(
                self._call_claude,
                messages,
                container_id
            )

            # Extract response text
            response_text = self._extract_text(response)

            # Check for tool use
            tool_used = False
            tool_result = None

            for block in response.content:
                if getattr(block, 'type', None) == 'tool_use':
                    tool_used = True
                    if block.name == 'recommend_advocates':
                        # Will be handled by matching service
                        tool_result = block.input

            # Extract case profile if present
            case_profile = self._extract_case_profile(response_text)

            # Get new container ID if available
            new_container_id = getattr(response, 'container_id', None) or container_id

            return response_text, new_container_id, case_profile, tool_used

        except Exception as e:
            logger.error(f"Error processing AI message: {e}")
            return f"I apologize, but I encountered an error. Please try again.", container_id, None, False

    def _build_messages(
        self,
        history: List[Dict[str, Any]],
        new_message: str
    ) -> List[Dict[str, Any]]:
        """Build messages list for Claude API."""
        messages = []

        # Add conversation history
        for msg in history[-20:]:  # Limit to last 20 messages
            role = "user" if msg.get("sender_type") == "client" else "assistant"
            messages.append({
                "role": role,
                "content": msg.get("content", "")
            })

        # Add new user message
        messages.append({
            "role": "user",
            "content": new_message
        })

        return messages

    def _call_claude(
        self,
        messages: List[Dict],
        container_id: Optional[str] = None
    ) -> Any:
        """Make synchronous call to Claude API."""
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "tools": [RECOMMEND_ADVOCATES_TOOL]
        }

        if container_id:
            kwargs["container_id"] = container_id

        return self.client.messages.create(**kwargs)

    def _extract_text(self, response) -> str:
        """Extract text content from Claude response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text') and block.text:
                text_parts.append(block.text)
        return "\n".join(text_parts) if text_parts else "I've processed your request."

    def _extract_case_profile(self, text: str) -> Optional[Dict]:
        """Extract case profile JSON from response text."""
        try:
            # Look for case_profile block
            if "```case_profile" in text:
                start = text.find("```case_profile") + len("```case_profile")
                end = text.find("```", start)
                if end > start:
                    json_str = text[start:end].strip()
                    return json.loads(json_str)

            # Look for general JSON that might be a case profile
            if '"matter_type"' in text and '"state"' in text:
                # Try to find and parse JSON
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    profile = json.loads(json_str)
                    if "matter_type" in profile:
                        return profile
        except json.JSONDecodeError:
            pass

        return None

    async def extract_case_profile_from_conversation(
        self,
        messages: List[Dict[str, Any]]
    ) -> Optional[Dict]:
        """
        Use AI to extract a case profile from conversation history.

        Args:
            messages: List of conversation messages

        Returns:
            Extracted case profile dict or None
        """
        if not self.client or not messages:
            return None

        # Build a summary prompt
        conversation_text = "\n".join([
            f"{'Client' if m.get('sender_type') == 'client' else 'AI'}: {m.get('content', '')}"
            for m in messages[-30:]
        ])

        extraction_prompt = f"""Based on the following legal consultation conversation, extract the case profile.
Return ONLY a JSON object with these fields (use null for unknown):

{{
  "matter_type": "civil|matrimonial|criminal|property|constitutional|conveyancing|notice",
  "sub_category": "specific issue like 'divorce petition', 'bail application'",
  "state": "Indian state name",
  "district": "district name",
  "court_level": "district|high_court|supreme_court|tribunal",
  "complexity": "simple|moderate|complex|highly_complex",
  "urgency": "urgent|normal|can_wait",
  "case_summary": "2-3 sentence summary of the case"
}}

Conversation:
{conversation_text}

JSON:"""

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": extraction_prompt}]
            )

            text = self._extract_text(response)

            # Parse JSON from response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])

        except Exception as e:
            logger.error(f"Error extracting case profile: {e}")

        return None


# Global instance
ai_service = AIService()
