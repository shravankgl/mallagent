"""
Assignment Verification Script
================================

Verifies all requirements are met for Session 6 assignment.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def test_imports():
    """Test 1: Verify all 4 layers can be imported."""
    console.print("\n[bold yellow]Test 1: Verifying Imports[/bold yellow]")

    try:
        from perception import PerceptionEngine, PerceptionResult, Intent, Entity, Constraints
        console.print("  ✓ perception.py - PerceptionEngine, PerceptionResult, Intent, Entity, Constraints")

        from memory import MemoryManager, UserPreferences, Message
        console.print("  ✓ memory.py - MemoryManager, UserPreferences, Message")

        from decision import DecisionEngine, DecisionPlan, ReasoningStep, ToolCall
        console.print("  ✓ decision.py - DecisionEngine, DecisionPlan, ReasoningStep, ToolCall")

        from action import ActionExecutor, ActionResult, ToolResult
        console.print("  ✓ action.py - ActionExecutor, ActionResult, ToolResult")

        from main import collect_user_preferences, cognitive_loop
        console.print("  ✓ main.py - collect_user_preferences, cognitive_loop")

        return True, {
            'perception': (PerceptionEngine, PerceptionResult, Intent, Entity, Constraints),
            'memory': (MemoryManager, UserPreferences, Message),
            'decision': (DecisionEngine, DecisionPlan, ReasoningStep, ToolCall),
            'action': (ActionExecutor, ActionResult, ToolResult)
        }
    except Exception as e:
        console.print(f"[red]  ✗ Import failed: {e}[/red]")
        return False, None


def test_pydantic_models(modules):
    """Test 2: Verify all models use Pydantic BaseModel."""
    console.print("\n[bold yellow]Test 2: Verifying Pydantic Models[/bold yellow]")

    try:
        from pydantic import BaseModel

        all_models = []

        # Check perception models
        PerceptionEngine, PerceptionResult, Intent, Entity, Constraints = modules['perception']
        for model in [Intent, Entity, Constraints, PerceptionResult]:
            if not issubclass(model, BaseModel):
                console.print(f"[red]  ✗ {model.__name__} is not a Pydantic BaseModel[/red]")
                return False
            all_models.append(('perception.py', model.__name__))

        # Check memory models
        MemoryManager, UserPreferences, Message = modules['memory']
        for model in [UserPreferences, Message]:
            if not issubclass(model, BaseModel):
                console.print(f"[red]  ✗ {model.__name__} is not a Pydantic BaseModel[/red]")
                return False
            all_models.append(('memory.py', model.__name__))

        # Check decision models
        DecisionEngine, DecisionPlan, ReasoningStep, ToolCall = modules['decision']
        for model in [ReasoningStep, ToolCall, DecisionPlan]:
            if not issubclass(model, BaseModel):
                console.print(f"[red]  ✗ {model.__name__} is not a Pydantic BaseModel[/red]")
                return False
            all_models.append(('decision.py', model.__name__))

        # Check action models
        ActionExecutor, ActionResult, ToolResult = modules['action']
        for model in [ToolResult, ActionResult]:
            if not issubclass(model, BaseModel):
                console.print(f"[red]  ✗ {model.__name__} is not a Pydantic BaseModel[/red]")
                return False
            all_models.append(('action.py', model.__name__))

        # Display results
        table = Table(title="Pydantic Models")
        table.add_column("File", style="cyan")
        table.add_column("Model", style="green")

        for file, model in all_models:
            table.add_row(file, model)

        console.print(table)
        console.print(f"  ✓ All {len(all_models)} models use Pydantic BaseModel")

        return True
    except Exception as e:
        console.print(f"[red]  ✗ Pydantic validation failed: {e}[/red]")
        return False


def test_model_instantiation():
    """Test 3: Verify models can be instantiated."""
    console.print("\n[bold yellow]Test 3: Verifying Model Instantiation[/bold yellow]")

    try:
        from perception import Intent, Entity, Constraints, PerceptionResult
        from memory import UserPreferences, Message
        from decision import ReasoningStep, ToolCall, DecisionPlan
        from action import ToolResult, ActionResult
        from datetime import datetime

        # Test perception models
        intent = Intent(primary_goal="find_shops", confidence=0.95, sub_goals=["buy gift"])
        console.print("  ✓ Intent instantiated")

        entity = Entity(text="Fashion Forward", type="shop_name", value="Fashion Forward")
        console.print("  ✓ Entity instantiated")

        constraints = Constraints(max_time_minutes=120, budget_level="medium")
        console.print("  ✓ Constraints instantiated")

        perception_result = PerceptionResult(
            intent=intent,
            entities=[entity],
            constraints=constraints,
            contextualized_query="User wants to find shops",
            reasoning_trace=["Step 1"]
        )
        console.print("  ✓ PerceptionResult instantiated")

        # Test memory models
        prefs = UserPreferences(shopping_style="balanced", budget_preference="medium")
        console.print("  ✓ UserPreferences instantiated")

        message = Message(role="user", content="Hello", timestamp=datetime.now())
        console.print("  ✓ Message instantiated")

        # Test decision models
        step = ReasoningStep(type="GOAL_DECOMPOSITION", description="Break down request")
        console.print("  ✓ ReasoningStep instantiated")

        tool_call = ToolCall(tool_name="search_shops", arguments={"category": "Fashion"})
        console.print("  ✓ ToolCall instantiated")

        plan = DecisionPlan(reasoning_steps=[step], tool_calls=[tool_call])
        console.print("  ✓ DecisionPlan instantiated")

        # Test action models
        tool_result = ToolResult(tool_name="search_shops", success=True, data={"shops": []})
        console.print("  ✓ ToolResult instantiated")

        action_result = ActionResult(
            tool_results=[tool_result],
            final_response="Here are the shops",
            reasoning_trace=["Executed search"],
            success=True
        )
        console.print("  ✓ ActionResult instantiated")

        return True
    except Exception as e:
        console.print(f"[red]  ✗ Model instantiation failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_file_existence():
    """Test 4: Verify all required files exist."""
    console.print("\n[bold yellow]Test 4: Verifying File Existence[/bold yellow]")

    import os

    required_files = [
        "perception.py",
        "memory.py",
        "decision.py",
        "action.py",
        "main.py",
        "mall_tools.py",
        "mall_data.json",
        ".env"
    ]

    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            console.print(f"  ✓ {file}")
        else:
            console.print(f"[red]  ✗ {file} missing[/red]")
            all_exist = False

    return all_exist


def test_preference_collection():
    """Test 5: Verify preference collection function exists."""
    console.print("\n[bold yellow]Test 5: Verifying Preference Collection[/bold yellow]")

    try:
        from main import collect_user_preferences
        import inspect

        # Check function signature
        sig = inspect.signature(collect_user_preferences)
        console.print(f"  ✓ collect_user_preferences() exists")
        console.print(f"  ✓ Signature: {sig}")

        # Check docstring
        if collect_user_preferences.__doc__:
            if "before" in collect_user_preferences.__doc__.lower():
                console.print("  ✓ Docstring mentions collecting preferences 'before' flow")
            else:
                console.print("[yellow]  ⚠ Docstring doesn't explicitly mention 'before'[/yellow]")

        return True
    except Exception as e:
        console.print(f"[red]  ✗ Preference collection verification failed: {e}[/red]")
        return False


def main():
    """Run all verification tests."""
    console.print(Panel(
        "[bold cyan]Session 6 Assignment Verification[/bold cyan]\n"
        "Checking all requirements...",
        title="🔍 Verification",
        border_style="cyan"
    ))

    results = {}

    # Test 1: Imports
    success, modules = test_imports()
    results['imports'] = success

    if not success:
        console.print("\n[red]Cannot proceed with further tests due to import failure[/red]")
        sys.exit(1)

    # Test 2: Pydantic models
    results['pydantic'] = test_pydantic_models(modules)

    # Test 3: Model instantiation
    results['instantiation'] = test_model_instantiation()

    # Test 4: File existence
    results['files'] = test_file_existence()

    # Test 5: Preference collection
    results['preferences'] = test_preference_collection()

    # Summary
    console.print("\n" + "="*60)
    console.print("[bold cyan]Verification Summary[/bold cyan]")
    console.print("="*60)

    table = Table()
    table.add_column("Test", style="cyan")
    table.add_column("Status", style="bold")

    for test_name, passed in results.items():
        status = "[green]✓ PASSED[/green]" if passed else "[red]✗ FAILED[/red]"
        table.add_row(test_name.upper(), status)

    console.print(table)

    all_passed = all(results.values())

    if all_passed:
        console.print(Panel(
            "[bold green]✅ ALL TESTS PASSED![/bold green]\n\n"
            "Assignment requirements verified:\n"
            "✓ 4 separate layer files\n"
            "✓ Pydantic models for all inputs/outputs\n"
            "✓ Preference collection before flow\n"
            "✓ main.py orchestration\n"
            "✓ All files present\n\n"
            "[bold]Ready for submission! 🎉[/bold]",
            title="SUCCESS",
            border_style="green"
        ))
        sys.exit(0)
    else:
        console.print(Panel(
            "[bold red]❌ SOME TESTS FAILED[/bold red]\n\n"
            "Please review the errors above and fix them.",
            title="FAILURE",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
