"""
Layer Logger - Structured logging for 4-layer cognitive architecture

Provides rich console logging to help instructors evaluate the cognitive flow:
- Layer transitions
- Input/output at each layer
- Processing steps
- LLM calls
"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from typing import Any, Dict, List
import json
import os

# Create console instance
console = Console()

# Check environment variable for logging level
VERBOSE_LOGGING = os.getenv("MALL_AGENT_DEBUG", "0") == "1"


class LayerLogger:
    """Structured logging for cognitive layers with rich formatting."""

    @staticmethod
    def log_layer_start(layer_name: str, layer_number: int):
        """Log layer activation with visual separator."""
        if VERBOSE_LOGGING:
            console.print(f"\n[bold cyan]{'='*70}[/bold cyan]")
            console.print(f"[bold cyan]LAYER {layer_number}: {layer_name.upper()}[/bold cyan]")
            console.print(f"[bold cyan]{'='*70}[/bold cyan]")
        else:
            console.print(f"\n[cyan]→ Layer {layer_number}: {layer_name}[/cyan]")

    @staticmethod
    def log_input(data: Any, title: str = "Input"):
        """Log layer input with JSON formatting."""
        if not VERBOSE_LOGGING:
            return

        # Convert Pydantic models to dict
        if hasattr(data, 'dict'):
            data = data.dict()
        elif hasattr(data, 'model_dump'):
            data = data.model_dump()

        try:
            json_str = json.dumps(data, indent=2, default=str)
            console.print(Panel(
                Syntax(json_str, "json", theme="monokai", line_numbers=False),
                title=f"[yellow]{title}[/yellow]",
                border_style="yellow",
                expand=False
            ))
        except Exception as e:
            console.print(Panel(
                str(data),
                title=f"[yellow]{title}[/yellow]",
                border_style="yellow"
            ))

    @staticmethod
    def log_processing(message: str):
        """Log processing step."""
        console.print(f"[dim]  → {message}[/dim]")

    @staticmethod
    def log_output(data: Any, title: str = "Output"):
        """Log layer output with structured display."""
        if not VERBOSE_LOGGING:
            return

        # Convert Pydantic models to dict
        if hasattr(data, 'dict'):
            data = data.dict()
        elif hasattr(data, 'model_dump'):
            data = data.model_dump()

        try:
            json_str = json.dumps(data, indent=2, default=str)
            console.print(Panel(
                Syntax(json_str, "json", theme="monokai", line_numbers=False),
                title=f"[green]{title}[/green]",
                border_style="green",
                expand=False
            ))
        except Exception as e:
            console.print(Panel(
                str(data),
                title=f"[green]{title}[/green]",
                border_style="green"
            ))

    @staticmethod
    def log_llm_call(model: str, prompt_preview: str):
        """Log LLM invocation."""
        if VERBOSE_LOGGING:
            console.print(Panel(
                f"[cyan]Model:[/cyan] {model}\n"
                f"[cyan]Prompt Preview:[/cyan] {prompt_preview[:150]}...",
                title="[blue]LLM Call[/blue]",
                border_style="blue",
                expand=False
            ))
        else:
            console.print(f"[dim]  → Calling LLM ({model})[/dim]")

    @staticmethod
    def log_tool_call(tool_name: str, params: Dict[str, Any]):
        """Log tool execution."""
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        console.print(f"[dim]  → Executing tool: {tool_name}({params_str})[/dim]")

    @staticmethod
    def log_tool_result(tool_name: str, success: bool, execution_time_ms: float):
        """Log tool result."""
        status = "✓ Success" if success else "✗ Failed"
        color = "green" if success else "red"
        console.print(f"[{color}]    {status}[/{color}] [dim]({execution_time_ms:.0f}ms)[/dim]")

    @staticmethod
    def log_error(message: str, error: Exception = None):
        """Log error with details."""
        error_panel = f"[red]{message}[/red]"
        if error and VERBOSE_LOGGING:
            error_panel += f"\n[dim]{str(error)}[/dim]"
        console.print(Panel(error_panel, title="[red]Error[/red]", border_style="red"))

    @staticmethod
    def log_fallback(layer_name: str, reason: str):
        """Log fallback activation."""
        console.print(f"[yellow]  ⚠ {layer_name} using fallback: {reason}[/yellow]")

    @staticmethod
    def log_summary(title: str, items: List[str]):
        """Log summary information."""
        console.print(f"\n[bold]{title}:[/bold]")
        for item in items:
            console.print(f"  • {item}")
