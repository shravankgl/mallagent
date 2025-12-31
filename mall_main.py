import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import AsyncAnthropic
import asyncio
from rich.console import Console
from rich.panel import Panel
import time
import json

console = Console()

# Load environment variables and setup Claude
load_dotenv()
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Rate limiting for Claude API Tier 1
class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 5):
        self.max_requests = max_requests_per_minute
        self.request_times = []
        self.daily_request_count = 0
        self.daily_reset_time = time.time() + 86400

    async def acquire(self):
        current_time = time.time()
        if current_time >= self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = current_time + 86400

        self.request_times = [t for t in self.request_times if current_time - t < 60]

        if len(self.request_times) >= self.max_requests:
            oldest_request = self.request_times[0]
            wait_time = 60 - (current_time - oldest_request) + 1
            if wait_time > 0:
                console.print(f"[yellow]Rate limit reached. Waiting {wait_time:.1f}s...[/yellow]")
                await asyncio.sleep(wait_time)
                current_time = time.time()
                self.request_times = [t for t in self.request_times if current_time - t < 60]

        self.request_times.append(current_time)
        self.daily_request_count += 1

rate_limiter = RateLimiter(max_requests_per_minute=4)

async def generate_with_timeout(client, prompt, timeout=30):
    try:
        await rate_limiter.acquire()
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            ),
            timeout=timeout
        )
        return response
    except asyncio.TimeoutError:
        console.print(f"[red]Request timed out after {timeout}s[/red]")
        return None
    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str.lower() or "429" in error_str or "overloaded" in error_str.lower():
            console.print(f"[yellow]Rate limit exceeded or API overloaded.[/yellow]")
        console.print(f"[red]Error: {error_str}[/red]")
        return None

async def main():
    try:
        console.print(Panel("🛍️  Shopping Mall Front Desk Agent", border_style="cyan", subtitle="Multi-Step Reasoning & Planning"))

        server_params = StdioServerParameters(
            command="python",
            args=["mall_tools.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                system_prompt = """You are an intelligent Shopping Mall Front Desk Agent that helps visitors plan their mall experience using step-by-step reasoning.

You have access to these tools:

CORE PLANNING TOOLS:
- show_reasoning(steps: list) - Display your step-by-step reasoning process
- search_shops(category, floor, keyword) - Search for shops
- get_shop_details(shop_name) - Get detailed shop information
- calculate_route(shop_ids: list) - Calculate optimized route
- verify_route(shop_ids: list, constraints: dict) - Verify route meets constraints
- get_recommendations(context, preferences) - Get context-aware recommendations
- check_shop_hours(shop_name, current_time) - Check if shop is open

ACCESSIBILITY TOOLS:
- get_accessibility_info(shop_name) - Get wheelchair access, elevator info, etc.
- calculate_accessible_route(shop_ids: list) - Route optimized for accessibility needs

FACILITIES & SERVICES:
- get_mall_facilities(facility_type) - Find restrooms, ATMs, nursing rooms, parking
- get_current_events() - Current promotions, events, and activities
- check_wait_time(location_name) - Check crowd levels and wait times

LOST & FOUND:
- log_lost_item(description, location, contact_info) - Report a lost item
- search_lost_and_found(item_type) - Search for found items

CRITICAL INSTRUCTIONS:

1. ✅ EXPLICIT REASONING: Always show your reasoning FIRST using show_reasoning()
   - Break down the user's request into clear steps
   - Identify what information you need
   - Plan your approach

2. ✅ STRUCTURED OUTPUT: Respond with EXACTLY ONE line:
   FUNCTION_CALL: {"name": "function_name", "args": {...}}
   OR
   FINAL_ANSWER: [Your complete answer]

3. ✅ TOOL SEPARATION: Clearly separate reasoning from tool execution:
   - First: show_reasoning (thinking)
   - Then: search/calculate/verify tools (doing)
   - Finally: verify and answer

4. ✅ REASONING TYPE AWARENESS: Tag each step:
   - [GOAL_DECOMPOSITION] Breaking down multi-part request
   - [CONSTRAINT_ANALYSIS] Identifying requirements (time, budget, accessibility)
   - [SEARCH_STRATEGY] Planning which tools to use
   - [ROUTE_OPTIMIZATION] Calculating efficient paths
   - [VERIFICATION] Checking if solution meets constraints
   - [FALLBACK_PLANNING] Providing alternatives

5. ✅ INTERNAL SELF-CHECKS: After each step:
   - "Does this answer the user's question?"
   - "Have I checked all constraints?"
   - "Is there a better approach?"

6. ✅ ERROR HANDLING: If tool fails:
   - Explain what went wrong
   - Provide alternative suggestions
   - Ask clarifying questions

7. ✅ CONVERSATION LOOP: Maintain context:
   - Remember previous searches
   - Build on earlier reasoning
   - Track satisfied constraints

EXAMPLE:
User: I need a gift for my wife who loves fashion, then lunch. 2 hours, lower floors only.
Assistant: FUNCTION_CALL: {"name": "show_reasoning", "args": {"steps": ["[GOAL_DECOMPOSITION] User has two goals: 1) Buy fashion gift 2) Have lunch", "[CONSTRAINT_ANALYSIS] Constraints: Time=2hrs, Location=lower floors (1-2)", "[SEARCH_STRATEGY] Will search: fashion shops on floors 1-2, then food options", "[ROUTE_OPTIMIZATION] Need to calculate efficient route", "[VERIFICATION] Must verify time constraint is met"]}}
User: Reasoning shown. Next?
Assistant: FUNCTION_CALL: {"name": "search_shops", "args": {"category": "Fashion", "floor": 1}}
User: Found Fashion Forward on Floor 1.
Assistant: FUNCTION_CALL: {"name": "search_shops", "args": {"category": "Food"}}
User: Found multiple food options.
Assistant: FUNCTION_CALL: {"name": "calculate_route", "args": {"shop_ids": [1, 3]}}
User: Route calculated.
Assistant: FUNCTION_CALL: {"name": "verify_route", "args": {"shop_ids": [1, 3], "constraints": {"max_time_minutes": 120, "lower_floors_only": true}}}
User: Route verified successfully.
Assistant: FINAL_ANSWER: [Perfect! I've planned your 2-hour visit on lower floors: 1) Fashion Forward (Floor 1) for your wife's gift 2) Food Court Central (Floor 3... wait, Floor 3 isn't lower! Let me recalculate...]

Remember: ALWAYS reason first, then act, then verify!"""

                # Test query
                query = "I'm planning an anniversary surprise. I need jewelry, a nice restaurant, and want lower floors for accessibility. Budget is flexible but I have only 90 minutes."
                console.print(Panel(f"Query: {query}", border_style="green"))

                prompt = f"{system_prompt}\n\nUser Query: {query}\n\nBegin your response:"
                conversation_history = []
                max_turns = 15

                for turn in range(max_turns):
                    response = await generate_with_timeout(client, prompt)
                    if not response or not response.content[0].text:
                        break

                    result = response.content[0].text.strip()
                    console.print(f"\n[yellow]Assistant Turn {turn+1}:[/yellow] {result[:200]}...")

                    if result.startswith("FUNCTION_CALL:"):
                        try:
                            _, function_info = result.split(":", 1)
                            func_data = json.loads(function_info.strip())
                            func_name = func_data["name"]
                            func_args = func_data.get("args", {})

                            console.print(f"[cyan]→ Calling: {func_name}({func_args})[/cyan]")

                            # Call the appropriate tool (dynamically)
                            try:
                                tool_result = await session.call_tool(func_name, arguments=func_args)
                            except Exception as e:
                                console.print(f"[red]Error calling {func_name}: {e}[/red]")
                                tool_result = None

                            if tool_result and tool_result.content:
                                result_text = tool_result.content[0].text
                                console.print(f"[green]← Result: {result_text[:150]}...[/green]")
                                prompt += f"\nAssistant: {result}\nUser: Tool result: {result_text}\nAssistant:"
                            else:
                                prompt += f"\nAssistant: {result}\nUser: Tool executed. Next step?\nAssistant:"

                        except json.JSONDecodeError as e:
                            console.print(f"[red]JSON parse error: {e}[/red]")
                            break
                        except Exception as e:
                            console.print(f"[red]Error executing tool: {e}[/red]")
                            break

                    elif result.startswith("FINAL_ANSWER:"):
                        answer = result.replace("FINAL_ANSWER:", "").strip()
                        console.print(Panel(f"[bold green]Final Answer:[/bold green]\n{answer}", border_style="green"))
                        break
                    else:
                        # Model didn't follow format, prompt it again
                        prompt += f"\nAssistant: {result}\nUser: Please respond with FUNCTION_CALL or FINAL_ANSWER format.\nAssistant:"

                console.print("\n[green]Session completed![/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
