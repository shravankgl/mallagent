"""
4-Layer Cognitive Architecture Mall Agent
==========================================

Architecture:
1. Perception Layer (LLM) - Understand user intent
2. Memory Layer - Track state and preferences
3. Decision-Making Layer - Plan actions
4. Action Layer - Execute tools and respond

Assignment Requirements:
- Ask user preferences BEFORE agentic flow starts
- Use Pydantic for all inputs/outputs
- Connect to MCP tools server
- Implement conversation loop
"""

import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import AsyncAnthropic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import time

# Import all 4 cognitive layers
from perception import PerceptionEngine, PerceptionResult
from memory import MemoryManager, UserPreferences
from decision import DecisionEngine, DecisionPlan
from action import ActionExecutor, ActionResult

console = Console()

# Load environment variables
load_dotenv()


class RateLimiter:
    """Rate limiting for Claude API Tier 1."""
    def __init__(self, max_requests_per_minute: int = 5):
        self.max_requests = max_requests_per_minute
        self.request_times = []

    async def acquire(self):
        current_time = time.time()
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


def collect_user_preferences() -> dict:
    """
    Collect user preferences BEFORE agentic flow starts.

    Assignment requirement: "need to ask the user about their preference
    'before' your agentic flow starts"

    Returns:
        dict: User preferences
    """
    console.print(Panel(
        "[bold cyan]Welcome to Grand Plaza Shopping Mall![/bold cyan]\n\n"
        "Before we begin, let me understand your preferences to serve you better.",
        title="🛍️  Mall Assistant",
        border_style="cyan"
    ))

    # Question 1: Shopping Style
    console.print("\n[bold]1. What's your shopping style today?[/bold]")
    console.print("   [cyan]quick[/cyan] - Fast in and out")
    console.print("   [cyan]browsing[/cyan] - Just looking around")
    console.print("   [cyan]balanced[/cyan] - Some planning, some exploration")
    console.print("   [cyan]thorough[/cyan] - Detailed planning and comparison")

    shopping_style = Prompt.ask(
        "Your choice",
        choices=["quick", "browsing", "balanced", "thorough"],
        default="balanced"
    )

    # Question 2: Budget
    console.print("\n[bold]2. What's your budget preference?[/bold]")
    console.print("   [cyan]low[/cyan] - Budget-conscious ($ range)")
    console.print("   [cyan]medium[/cyan] - Moderate spending ($$ range)")
    console.print("   [cyan]high[/cyan] - Premium options ($$$ range)")

    budget_preference = Prompt.ask(
        "Your choice",
        choices=["low", "medium", "high"],
        default="medium"
    )

    # Question 3: Preferred Categories
    console.print("\n[bold]3. What categories are you interested in?[/bold]")
    console.print("   Options: Fashion, Electronics, Food, Books, Jewelry, Beauty, Sports, Toys, Home, etc.")
    console.print("   [dim](Enter comma-separated list, or press Enter to skip)[/dim]")

    categories_input = Prompt.ask("Your interests", default="")
    preferred_categories = [cat.strip() for cat in categories_input.split(",") if cat.strip()]

    # Question 4: Dietary Restrictions
    console.print("\n[bold]4. Any dietary restrictions?[/bold]")
    console.print("   Options: vegetarian, vegan, gluten-free, halal, kosher, etc.")
    console.print("   [dim](Enter comma-separated list, or press Enter to skip)[/dim]")

    dietary_input = Prompt.ask("Your restrictions", default="")
    dietary_restrictions = [d.strip() for d in dietary_input.split(",") if d.strip()]

    # Question 5: Accessibility Needs
    console.print("\n[bold]5. Do you have any accessibility needs?[/bold]")
    console.print("   Options: wheelchair, elevator-only, wide-aisles, visual-assistance, etc.")
    console.print("   [dim](Enter comma-separated list, or press Enter to skip)[/dim]")

    accessibility_input = Prompt.ask("Your needs", default="")
    accessibility_needs = [a.strip() for a in accessibility_input.split(",") if a.strip()]

    # Summary
    preferences = {
        "shopping_style": shopping_style,
        "budget_preference": budget_preference,
        "preferred_categories": preferred_categories,
        "dietary_restrictions": dietary_restrictions,
        "accessibility_needs": accessibility_needs
    }

    console.print(Panel(
        f"[bold green]✓ Preferences saved![/bold green]\n\n"
        f"Shopping Style: {shopping_style}\n"
        f"Budget: {budget_preference}\n"
        f"Categories: {preferred_categories or 'Any'}\n"
        f"Dietary: {dietary_restrictions or 'None'}\n"
        f"Accessibility: {accessibility_needs or 'None'}",
        title="Your Profile",
        border_style="green"
    ))

    return preferences


async def cognitive_loop(
    user_query: str,
    perception: PerceptionEngine,
    memory: MemoryManager,
    decision: DecisionEngine,
    action: ActionExecutor
) -> str:
    """
    Main cognitive loop: Perception → Memory → Decision → Action

    Args:
        user_query: User's input
        perception: Perception engine
        memory: Memory manager
        decision: Decision engine
        action: Action executor

    Returns:
        str: Final response to user
    """
    # Get user profile from memory
    user_profile = memory.get_preferences_dict()

    # LAYER 1: PERCEPTION - Understand user intent
    console.print("\n[dim]→ Layer 1: Perception (Understanding intent)...[/dim]")
    perception_result: PerceptionResult = await perception.perceive(user_query, user_profile)

    console.print(f"[cyan]  Intent: {perception_result.intent.primary_goal} "
                  f"(confidence: {perception_result.intent.confidence:.2f})[/cyan]")

    # LAYER 2: MEMORY - Store conversation and retrieve context
    console.print("[dim]→ Layer 2: Memory (Recording interaction)...[/dim]")
    memory.add_message("user", user_query)

    # Get recent context
    recent_context = memory.get_context_string()

    # LAYER 3: DECISION - Plan actions
    console.print("[dim]→ Layer 3: Decision (Planning actions)...[/dim]")
    decision_plan: DecisionPlan = await decision.decide(perception_result, user_profile)

    console.print(f"[yellow]  Planned {len(decision_plan.tool_calls)} tool calls[/yellow]")
    for tool_call in decision_plan.tool_calls:
        console.print(f"[yellow]    - {tool_call.tool_name}[/yellow]")

    # LAYER 4: ACTION - Execute tools and synthesize response
    console.print("[dim]→ Layer 4: Action (Executing tools)...[/dim]")
    action_result: ActionResult = await action.execute(decision_plan)

    # Store assistant response
    memory.add_message("assistant", action_result.final_response)

    console.print(f"[green]  ✓ Action complete (success: {action_result.success})[/green]")

    return action_result.final_response


async def main():
    """Main entry point for 4-layer cognitive architecture."""
    try:
        # Display welcome banner
        console.print(Panel(
            "[bold cyan]4-Layer Cognitive Architecture[/bold cyan]\n"
            "Perception → Memory → Decision → Action",
            title="🛍️  Grand Plaza Shopping Mall",
            border_style="cyan"
        ))

        # CRITICAL: Collect user preferences BEFORE agentic flow
        console.print("\n[bold yellow]Step 1: Collecting User Preferences[/bold yellow]")
        preferences = collect_user_preferences()

        # Initialize Claude client
        anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        rate_limiter = RateLimiter(max_requests_per_minute=4)

        # Initialize MCP tools server
        console.print("\n[bold yellow]Step 2: Connecting to MCP Tools Server[/bold yellow]")
        server_params = StdioServerParameters(
            command="python",
            args=["mall_tools.py"]
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as mcp_session:
                await mcp_session.initialize()
                console.print("[green]✓ MCP tools server connected[/green]")

                # List available tools
                tools_result = await mcp_session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                console.print(f"[green]✓ {len(tool_names)} tools available[/green]")

                # Initialize all 4 cognitive layers
                console.print("\n[bold yellow]Step 3: Initializing Cognitive Layers[/bold yellow]")

                # Layer 1: Perception
                perception = PerceptionEngine(anthropic_client)
                console.print("[green]✓ Layer 1: Perception Engine initialized[/green]")

                # Layer 2: Memory
                memory = MemoryManager()
                memory.set_preferences(preferences)
                console.print("[green]✓ Layer 2: Memory Manager initialized[/green]")

                # Layer 3: Decision
                decision = DecisionEngine(anthropic_client)
                console.print("[green]✓ Layer 3: Decision Engine initialized[/green]")

                # Layer 4: Action
                action = ActionExecutor(mcp_session)
                console.print("[green]✓ Layer 4: Action Executor initialized[/green]")

                # Conversation loop
                console.print("\n[bold yellow]Step 4: Starting Conversation Loop[/bold yellow]")
                console.print("[dim]Type 'quit' or 'exit' to end conversation[/dim]\n")

                while True:
                    # Get user input
                    user_input = Prompt.ask("\n[bold blue]You[/bold blue]")

                    if user_input.lower() in ["quit", "exit", "bye"]:
                        console.print(Panel(
                            "[bold green]Thank you for visiting Grand Plaza Shopping Mall![/bold green]\n"
                            "Have a great day!",
                            border_style="green"
                        ))
                        break

                    # Rate limiting
                    await rate_limiter.acquire()

                    # Run cognitive loop
                    try:
                        response = await cognitive_loop(
                            user_query=user_input,
                            perception=perception,
                            memory=memory,
                            decision=decision,
                            action=action
                        )

                        # Display response
                        console.print(Panel(
                            response,
                            title="[bold green]Assistant[/bold green]",
                            border_style="green"
                        ))

                    except Exception as e:
                        console.print(f"[red]Error in cognitive loop: {e}[/red]")
                        import traceback
                        traceback.print_exc()

    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
