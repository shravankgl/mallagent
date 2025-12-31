# Shopping Mall Agent - Prompt Validation

## Evaluation Against `prompt_of_prompts.md` Criteria

### 1. ✅ Explicit Reasoning Instructions

**Requirement**: Does the prompt tell the model to reason step-by-step?

**Our Implementation**:
```
1. ✅ EXPLICIT REASONING: Always show your reasoning FIRST using show_reasoning()
   - Break down the user's request into clear steps
   - Identify what information you need
   - Plan your approach
```

**Rating**: ✅ **PASS** - The prompt explicitly instructs the model to use `show_reasoning()` before any action, with clear instructions on what to include.

---

### 2. ✅ Structured Output Format

**Requirement**: Does the prompt enforce a predictable output format (e.g., FUNCTION_CALL, JSON, numbered steps)?

**Our Implementation**:
```
2. ✅ STRUCTURED OUTPUT: Respond with EXACTLY ONE line:
   FUNCTION_CALL: {"name": "function_name", "args": {...}}
   OR
   FINAL_ANSWER: [Your complete answer]
```

**Rating**: ✅ **PASS** - Enforces strict JSON format for function calls and clear final answer format. Easy to parse and validate.

---

### 3. ✅ Separation of Reasoning and Tools

**Requirement**: Are reasoning steps clearly separated from computation or tool-use steps?

**Our Implementation**:
```
3. ✅ TOOL SEPARATION: Clearly separate reasoning from tool execution:
   - First: show_reasoning (thinking)
   - Then: search/calculate/verify tools (doing)
   - Finally: verify and answer
```

**Rating**: ✅ **PASS** - Clear three-phase process: think → do → verify. Reasoning (`show_reasoning`) is always first, followed by action tools.

---

### 4. ✅ Conversation Loop Support

**Requirement**: Could this prompt work in a back-and-forth (multi-turn) setting?

**Our Implementation**:
```
7. ✅ CONVERSATION LOOP: Maintain context:
   - Remember previous searches
   - Build on earlier reasoning
   - Track satisfied constraints
```

Plus example showing multi-turn interaction with tool results feeding back into the prompt.

**Rating**: ✅ **PASS** - Designed for multi-turn conversations. The code maintains `conversation_history` and appends tool results to the prompt.

---

### 5. ✅ Instructional Framing

**Requirement**: Are there examples of desired behavior or "formats" to follow?

**Our Implementation**:
```
EXAMPLE:
User: I need a gift for my wife who loves fashion, then lunch. 2 hours, lower floors only.
Assistant: FUNCTION_CALL: {"name": "show_reasoning", "args": {"steps": ["[GOAL_DECOMPOSITION] User has two goals: 1) Buy fashion gift 2) Have lunch", "[CONSTRAINT_ANALYSIS] Constraints: Time=2hrs, Location=lower floors (1-2)", ...]}}
User: Reasoning shown. Next?
Assistant: FUNCTION_CALL: {"name": "search_shops", "args": {"category": "Fashion", "floor": 1}}
...
```

**Rating**: ✅ **PASS** - Comprehensive example showing the full workflow with proper reasoning tags and tool calls.

---

### 6. ✅ Internal Self-Checks

**Requirement**: Does the prompt instruct the model to self-verify or sanity-check intermediate steps?

**Our Implementation**:
```
5. ✅ INTERNAL SELF-CHECKS: After each step:
   - "Does this answer the user's question?"
   - "Have I checked all constraints?"
   - "Is there a better approach?"
```

Plus a dedicated `verify_route()` tool for formal verification.

**Rating**: ✅ **PASS** - Explicit self-check questions after each step, plus formal verification tool.

---

### 7. ✅ Reasoning Type Awareness

**Requirement**: Does the prompt encourage the model to tag or identify the type of reasoning used?

**Our Implementation**:
```
4. ✅ REASONING TYPE AWARENESS: Tag each step:
   - [GOAL_DECOMPOSITION] Breaking down multi-part request
   - [CONSTRAINT_ANALYSIS] Identifying requirements (time, budget, accessibility)
   - [SEARCH_STRATEGY] Planning which tools to use
   - [ROUTE_OPTIMIZATION] Calculating efficient paths
   - [VERIFICATION] Checking if solution meets constraints
   - [FALLBACK_PLANNING] Providing alternatives
```

**Rating**: ✅ **PASS** - Six distinct reasoning types with clear tags. Example shows proper usage.

---

### 8. ✅ Error Handling or Fallbacks

**Requirement**: Does the prompt specify what to do if an answer is uncertain, a tool fails, or the model is unsure?

**Our Implementation**:
```
6. ✅ ERROR HANDLING: If tool fails:
   - Explain what went wrong
   - Provide alternative suggestions
   - Ask clarifying questions
```

**Rating**: ✅ **PASS** - Clear instructions on error handling with three-step response strategy.

---

### 9. ✅ Overall Clarity and Robustness

**Requirement**: Is the prompt easy to follow? Is it likely to reduce hallucination and drift?

**Our Analysis**:
- ✅ Clear numbered sections
- ✅ Explicit format requirements
- ✅ Concrete example showing expected behavior
- ✅ Systematic reasoning tags prevent drift
- ✅ Verification step reduces hallucination
- ✅ Tool separation maintains focus

**Rating**: ✅ **PASS** - Well-structured, comprehensive, and includes guardrails against common LLM failure modes.

---

## Summary Evaluation

```json
{
  "explicit_reasoning": true,
  "structured_output": true,
  "tool_separation": true,
  "conversation_loop": true,
  "instructional_framing": true,
  "internal_self_checks": true,
  "reasoning_type_awareness": true,
  "fallbacks": true,
  "overall_clarity": "Excellent structure with comprehensive reasoning framework, clear tool separation, formal verification, and robust error handling. The prompt enforces systematic thinking while maintaining flexibility for complex multi-step queries."
}
```

**VERDICT**: ✅ **ALL CRITERIA PASSED** (9/9)

The Shopping Mall Agent prompt meets all requirements from `prompt_of_prompts.md` and demonstrates best practices for chain-of-thought reasoning in LLM applications.
