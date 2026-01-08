# 4-Layer Cognitive Architecture - Mall Agent

## Overview

Complete implementation of 4-layer cognitive architecture for shopping mall assistant agent.

**Assignment Requirements Met:**
- ✅ 4 separate files for each cognitive layer
- ✅ All inputs/outputs use Pydantic models
- ✅ User preferences collected BEFORE agentic flow
- ✅ main.py orchestrates complete agent
- ✅ Integrates with MCP tools from mall_main.py

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER INPUT                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  USER PREFERENCES     │  ← Collected BEFORE flow
        │  (shopping_style,     │
        │   budget, categories) │
        └──────────┬────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 1: PERCEPTION (LLM)                           │
│  - Intent classification                              │
│  - Entity extraction                                  │
│  - Constraint analysis                                │
│  - Uses user preferences in context                   │
│  Model: Claude Haiku 4.5                             │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 2: MEMORY                                     │
│  - Store conversation history                         │
│  - Track user preferences                             │
│  - Provide context                                    │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 3: DECISION-MAKING (LLM)                      │
│  - Multi-step reasoning                               │
│  - Tool selection                                     │
│  - Plan generation                                    │
│  - 6 reasoning types                                  │
│  Model: Claude Sonnet 4.5                            │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  LAYER 4: ACTION                                     │
│  - Execute MCP tools                                  │
│  - Synthesize responses                               │
│  - 14 mall-specific tools                             │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
                RESPONSE
```

---

## File Structure

### Core Cognitive Layers

#### 1. [perception.py](perception.py)
**Purpose:** Understand user intent using LLM

**Pydantic Models:**
- `Intent` - Primary goal, sub-goals, confidence
- `Entity` - Named entities (shops, floors, categories)
- `Constraints` - Time, budget, floor, accessibility
- `PerceptionResult` - Complete perception output

**Key Class:**
```python
class PerceptionEngine:
    async def perceive(
        self,
        user_query: str,
        user_profile: dict = None
    ) -> PerceptionResult
```

**Features:**
- LLM-powered intent classification
- User preference integration
- Confidence scoring
- Reasoning trace

---

#### 2. [memory.py](memory.py)
**Purpose:** State management and conversation tracking

**Pydantic Models:**
- `UserPreferences` - Shopping preferences
- `Message` - Conversation history

**Key Class:**
```python
class MemoryManager:
    def set_preferences(self, preferences: Dict[str, Any])
    def add_message(self, role: str, content: str)
    def get_recent_context(self, n: int = 5) -> List[Message]
    def get_context_string(self) -> str
```

**Features:**
- Stores user preferences (collected at startup)
- Tracks conversation history
- Provides context for other layers

---

#### 3. [decision.py](decision.py)
**Purpose:** Multi-step reasoning and planning

**Pydantic Models:**
- `ReasoningStep` - Single reasoning step with type
- `ToolCall` - Tool to execute with arguments
- `DecisionPlan` - Complete decision output

**Key Class:**
```python
class DecisionEngine:
    async def decide(
        self,
        perception: PerceptionResult,
        user_profile: dict
    ) -> DecisionPlan
```

**6 Reasoning Types:**
1. `GOAL_DECOMPOSITION` - Break down complex requests
2. `CONSTRAINT_ANALYSIS` - Identify requirements
3. `SEARCH_STRATEGY` - Plan tool usage
4. `ROUTE_OPTIMIZATION` - Calculate efficient paths
5. `VERIFICATION` - Check if solution meets constraints
6. `FALLBACK_PLANNING` - Provide alternatives

**Features:**
- LLM-powered planning (Claude Sonnet)
- Structured reasoning traces
- Tool call generation
- User preference awareness

---

#### 4. [action.py](action.py)
**Purpose:** Execute tools and synthesize responses

**Pydantic Models:**
- `ToolResult` - Individual tool execution result
- `ActionResult` - Complete action output

**Key Class:**
```python
class ActionExecutor:
    async def execute(self, plan: DecisionPlan) -> ActionResult
```

**Features:**
- Executes MCP tools from decision plan
- Handles tool errors gracefully
- Synthesizes natural language response
- Execution time tracking

---

### Orchestration

#### [main.py](main.py)
**Purpose:** Tie all 4 layers together

**Main Functions:**
1. `collect_user_preferences()` - Interactive questionnaire
2. `cognitive_loop()` - Perception → Memory → Decision → Action
3. `main()` - Entry point with MCP server connection

**Flow:**
```python
# Step 1: Collect preferences (BEFORE flow)
preferences = collect_user_preferences()

# Step 2: Initialize all 4 layers
perception = PerceptionEngine(client)
memory = MemoryManager()
decision = DecisionEngine(client)
action = ActionExecutor(mcp_session, client)

# Step 3: Conversation loop
while True:
    user_input = input()
    response = await cognitive_loop(
        user_input, perception, memory, decision, action
    )
    print(response)
```

---

## MCP Tools (14 Tools)

Connected via `mall_tools.py`:

### Core Planning Tools
1. `show_reasoning` - Display reasoning steps
2. `search_shops` - Search by category/floor/keyword
3. `get_shop_details` - Get detailed shop info
4. `calculate_route` - Optimized route planning
5. `verify_route` - Verify route meets constraints
6. `get_recommendations` - Context-aware suggestions
7. `check_shop_hours` - Check if shop is open

### Accessibility Tools
8. `get_accessibility_info` - Wheelchair access info
9. `calculate_accessible_route` - Accessible routing

### Facilities & Services
10. `get_mall_facilities` - Restrooms, ATMs, parking
11. `get_current_events` - Promotions and events
12. `check_wait_time` - Crowd levels

### Lost & Found
13. `log_lost_item` - Report lost item
14. `search_lost_and_found` - Search for found items

---

## User Preferences System

**Collected Before Flow:**
1. **Shopping Style:** quick, browsing, balanced, thorough
2. **Budget Preference:** low, medium, high
3. **Preferred Categories:** Fashion, Electronics, Food, etc.
4. **Dietary Restrictions:** vegetarian, vegan, gluten-free, etc.
5. **Accessibility Needs:** wheelchair, elevator-only, etc.

**Usage Throughout System:**
- **Perception:** Context for intent understanding
- **Decision:** Influences tool selection and recommendations
- **Action:** Personalized response synthesis

---

## Running the Agent

### Prerequisites
```bash
# Ensure .venv is activated
source .venv/bin/activate

# Or use .venv/bin/python3 directly
```

### Start the Agent
```bash
.venv/bin/python3 main.py
```

### Interactive Flow
```
Step 1: User Preference Collection
  → 5 questions about preferences
  → Saved to memory layer

Step 2: Connect to MCP Tools
  → Initialize mall_tools.py server
  → Load 14 tools

Step 3: Initialize Cognitive Layers
  ✓ Perception Engine
  ✓ Memory Manager
  ✓ Decision Engine
  ✓ Action Executor

Step 4: Conversation Loop
  User: "I need a gift for my wife"

  → Perception: Classify intent (find_shops)
  → Memory: Store message, retrieve context
  → Decision: Plan search strategy + tool calls
  → Action: Execute tools, synthesize response

  Assistant: [Personalized response based on preferences]
```

---

## Example Conversation

**User Preferences Collected:**
- Shopping Style: balanced
- Budget: medium
- Categories: Fashion, Jewelry
- Dietary: None
- Accessibility: wheelchair

**Conversation:**
```
User: I need an anniversary gift and lunch

→ Layer 1: Perception
  Intent: find_shops (confidence: 0.95)
  Entities: [anniversary, gift, lunch]
  Constraints: budget=medium, accessible=true

→ Layer 2: Memory
  Recording user message
  Context: First interaction

→ Layer 3: Decision
  Reasoning Steps:
    [GOAL_DECOMPOSITION] Two goals: gift + lunch
    [CONSTRAINT_ANALYSIS] Budget=medium, wheelchair accessible
    [SEARCH_STRATEGY] Search jewelry (user preference), then food

  Tool Calls:
    1. search_shops(category="Jewelry", floor=None)
    2. calculate_accessible_route(...)

→ Layer 4: Action
  Executing search_shops...
  Found: Jewelry Junction (Floor 2)

  Executing calculate_accessible_route...
  Route: Floor 1 → Elevator 1 → Floor 2

  Synthesizing response...