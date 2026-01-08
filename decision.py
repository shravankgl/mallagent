"""
Decision-Making Layer - Planning and reasoning

Converts perception into actionable plans using:
- Goal decomposition
- Tool selection
- Constraint solving
- Reasoning traces
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from perception import PerceptionResult
from anthropic import AsyncAnthropic
import json


# Pydantic Models
class ReasoningStep(BaseModel):
    """Single step of reasoning."""
    type: str = Field(..., description="Reasoning type: GOAL_DECOMPOSITION, CONSTRAINT_ANALYSIS, etc.")
    description: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ToolCall(BaseModel):
    """Tool execution request."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(default="", description="Why this tool")


class DecisionPlan(BaseModel):
    """Complete decision output."""
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    final_answer: Optional[str] = None
    verification_needed: bool = False


class DecisionEngine:
    """Multi-step reasoning and planning."""

    DECISION_PROMPT = """You are the Decision-Making Module of a mall assistant.

Given perception results, create an execution plan.

6 Reasoning Types:
1. [GOAL_DECOMPOSITION] - Break request into sub-goals
2. [CONSTRAINT_ANALYSIS] - Identify time/budget/location limits
3. [SEARCH_STRATEGY] - Plan which tools to use
4. [ROUTE_OPTIMIZATION] - Calculate efficient paths
5. [VERIFICATION] - Check constraint satisfaction
6. [FALLBACK_PLANNING] - Alternative if primary fails

Available Tools:
- show_reasoning(steps: list) - Display thinking
- search_shops(category: str, floor: int) - Find shops
- get_shop_details(shop_name: str) - Shop info
- calculate_route(shop_ids: list) - Optimize route
- verify_route(shop_ids: list, constraints: dict) - Check validity
- get_recommendations(context: str, preferences: dict) - Personalized suggestions
- get_accessibility_info(shop_name: str) - Accessibility details
- get_mall_facilities(type: str) - Restrooms, ATMs, etc.

Output JSON:
{
  "reasoning_steps": [
    {"type": "GOAL_DECOMPOSITION", "description": "Break into: find shop + route"},
    {"type": "SEARCH_STRATEGY", "description": "Use search_shops for Fashion"}
  ],
  "tool_calls": [
    {"tool_name": "show_reasoning", "arguments": {"steps": ["Step 1..."]}},
    {"tool_name": "search_shops", "arguments": {"category": "Fashion", "floor": 1}}
  ],
  "final_answer": null,
  "verification_needed": true
}
"""

    def __init__(self, anthropic_client: AsyncAnthropic):
        self.client = anthropic_client

    async def decide(
        self,
        perception: PerceptionResult,
        user_profile: dict,
        conversation_context: List[str] = None
    ) -> DecisionPlan:
        """Create action plan from perception.

        Args:
            perception: Output from perception layer
            user_profile: User preferences
            conversation_context: Recent conversation history

        Returns:
            DecisionPlan with reasoning and tool calls
        """
        try:
            # Build context
            context = f"""
Perception:
- Intent: {perception.intent.primary_goal} (confidence: {perception.intent.confidence})
- Query: {perception.contextualized_query}
- Entities: {[e.dict() for e in perception.entities]}
- Constraints: {perception.constraints.dict()}

User Profile:
- Shopping style: {user_profile.get('shopping_style')}
- Budget: {user_profile.get('budget_preference')}
- Preferred categories: {user_profile.get('preferred_categories')}
- Dietary: {user_profile.get('dietary_restrictions')}
"""

            # Call Claude
            message = await self.client.messages.create(
                model="claude-sonnet-4-5-20250929",  # Sonnet for reasoning
                max_tokens=2000,
                system=self.DECISION_PROMPT,
                messages=[{"role": "user", "content": context}]
            )

            # Parse
            response_text = message.content[0].text.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(response_text)

            # Convert to Pydantic
            reasoning_steps = [ReasoningStep(**step) for step in data.get("reasoning_steps", [])]
            tool_calls = [ToolCall(**tool) for tool in data.get("tool_calls", [])]

            return DecisionPlan(
                reasoning_steps=reasoning_steps,
                tool_calls=tool_calls,
                final_answer=data.get("final_answer"),
                verification_needed=data.get("verification_needed", False)
            )

        except Exception as e:
            print(f"Decision error: {e}, using fallback")
            return self._simple_fallback(perception)

    def _simple_fallback(self, perception: PerceptionResult) -> DecisionPlan:
        """Simple rule-based decision making."""
        intent = perception.intent.primary_goal

        if intent == "find_shops":
            # Extract category from entities
            category = "Fashion"  # Default
            for entity in perception.entities:
                if entity.type == "category":
                    category = entity.value

            return DecisionPlan(
                reasoning_steps=[
                    ReasoningStep(
                        type="GOAL_DECOMPOSITION",
                        description=f"Find {category} shops"
                    )
                ],
                tool_calls=[
                    ToolCall(
                        tool_name="search_shops",
                        arguments={"category": category},
                        reasoning=f"User wants to find {category} shops"
                    )
                ]
            )

        elif intent == "check_facilities":
            return DecisionPlan(
                reasoning_steps=[
                    ReasoningStep(
                        type="SEARCH_STRATEGY",
                        description="Look up mall facilities"
                    )
                ],
                tool_calls=[
                    ToolCall(
                        tool_name="get_mall_facilities",
                        arguments={"type": "all"},
                        reasoning="User asking about facilities"
                    )
                ]
            )

        else:  # get_directions
            return DecisionPlan(
                reasoning_steps=[
                    ReasoningStep(
                        type="SEARCH_STRATEGY",
                        description="Provide navigation help"
                    )
                ],
                final_answer="I can help you navigate. Which floor or shop are you looking for?"
            )
