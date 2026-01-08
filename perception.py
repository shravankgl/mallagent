"""
Perception Layer - Understanding user input with LLM

Converts raw text into structured cognitive representations using:
- Intent classification
- Entity extraction
- Constraint parsing
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic
import json


# Pydantic Models for Input/Output
class Intent(BaseModel):
    """User's primary goal."""
    primary_goal: str = Field(..., description="Main intent: find_shops, get_directions, check_facilities")
    sub_goals: List[str] = Field(default_factory=list, description="Additional goals")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")


class Entity(BaseModel):
    """Extracted entity from user query."""
    type: str = Field(..., description="Entity type: category, shop, floor, time, budget")
    value: str = Field(..., description="Entity value")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Constraints(BaseModel):
    """User constraints and preferences."""
    max_time_minutes: Optional[int] = None
    budget_range: Optional[str] = None  # "low", "medium", "high"
    preferred_floors: List[int] = Field(default_factory=list)
    accessibility_required: bool = False
    dietary_restrictions: List[str] = Field(default_factory=list)


class PerceptionResult(BaseModel):
    """Complete perception output."""
    intent: Intent
    entities: List[Entity] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    contextualized_query: str = Field(..., description="Rewritten query with context")
    reasoning_trace: List[str] = Field(default_factory=list)
    user_preferences_activated: List[str] = Field(default_factory=list)


class PerceptionEngine:
    """LLM-powered perception with fallback to keyword matching."""

    PERCEPTION_PROMPT = """You are the Perception Module of a mall assistant agent.

Classify user queries into one of these intents:
1. find_shops - User wants to find stores or buy products
2. get_directions - User needs navigation help
3. check_facilities - User asking about mall amenities

Extract entities:
- categories (Fashion, Electronics, Food, etc.)
- shop names
- floor numbers
- time constraints
- budget indicators

Respond with JSON ONLY:
{
  "intent": "find_shops",
  "confidence": 0.95,
  "entities": [
    {"type": "category", "value": "Fashion", "confidence": 0.9}
  ],
  "constraints": {
    "max_time_minutes": 90,
    "budget_range": "high",
    "preferred_floors": [1, 2]
  },
  "reasoning": "User mentioned buying shoes, indicates shopping intent"
}

Confidence scale:
- 0.9-1.0: Very clear
- 0.7-0.9: Likely
- 0.5-0.7: Uncertain
"""

    def __init__(self, anthropic_client: AsyncAnthropic):
        self.client = anthropic_client

    async def perceive(self, user_query: str, user_profile: dict = None) -> PerceptionResult:
        """Extract structured understanding from user query.

        Args:
            user_query: Raw user input
            user_profile: Optional user profile for context

        Returns:
            PerceptionResult with intent, entities, constraints
        """
        try:
            # Add user profile context to query
            context_prompt = self.PERCEPTION_PROMPT
            if user_profile:
                context_prompt += f"\n\nUser Profile Context:\n"
                context_prompt += f"- Shopping style: {user_profile.get('shopping_style', 'balanced')}\n"
                context_prompt += f"- Budget preference: {user_profile.get('budget_preference', 'medium')}\n"
                context_prompt += f"- Preferred categories: {', '.join(user_profile.get('preferred_categories', []))}\n"
                context_prompt += f"- Dietary restrictions: {', '.join(user_profile.get('dietary_restrictions', []))}\n"

            # Call Claude API
            message = await self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=context_prompt,
                messages=[{"role": "user", "content": user_query}]
            )

            # Parse response
            response_text = message.content[0].text.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)

            # Convert to Pydantic models
            intent = Intent(
                primary_goal=data.get("intent", "find_shops"),
                confidence=data.get("confidence", 0.5)
            )

            entities = [
                Entity(**ent) for ent in data.get("entities", [])
            ]

            constraints = Constraints(**(data.get("constraints", {})))

            return PerceptionResult(
                intent=intent,
                entities=entities,
                constraints=constraints,
                contextualized_query=user_query,
                reasoning_trace=[data.get("reasoning", "LLM classification")],
                user_preferences_activated=list(user_profile.keys()) if user_profile else []
            )

        except Exception as e:
            print(f"Perception error: {e}, using fallback")
            return self._keyword_fallback(user_query)

    def _keyword_fallback(self, user_query: str) -> PerceptionResult:
        """Simple keyword-based fallback."""
        query_lower = user_query.lower()

        keywords = {
            "find_shops": ["shop", "store", "buy", "purchase", "need"],
            "get_directions": ["where", "how to get", "direction"],
            "check_facilities": ["restroom", "parking", "ATM"]
        }

        intent_name = "find_shops"
        confidence = 0.5

        for intent, kws in keywords.items():
            if any(kw in query_lower for kw in kws):
                intent_name = intent
                confidence = 0.7
                break

        return PerceptionResult(
            intent=Intent(primary_goal=intent_name, confidence=confidence),
            entities=[],
            constraints=Constraints(),
            contextualized_query=user_query,
            reasoning_trace=["[Fallback] Keyword matching"],
            user_preferences_activated=[]
        )
