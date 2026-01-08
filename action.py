"""
Action Layer - Tool execution and response synthesis

Executes planned actions using:
- MCP tool calls
- Parallel execution
- Error recovery
- Response generation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from decision import DecisionPlan
from mcp import ClientSession
import asyncio


# Pydantic Models
class ToolResult(BaseModel):
    """Result from tool execution."""
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ActionResult(BaseModel):
    """Complete action output."""
    tool_results: List[ToolResult] = Field(default_factory=list)
    final_response: str
    reasoning_trace: List[str] = Field(default_factory=list)
    success: bool = True


class ActionExecutor:
    """Execute tools and synthesize responses."""

    def __init__(self, mcp_session: ClientSession):
        self.session = mcp_session

    async def execute(self, plan: DecisionPlan) -> ActionResult:
        """Execute decision plan.

        Args:
            plan: DecisionPlan from decision layer

        Returns:
            ActionResult with tool results and response
        """
        tool_results = []
        reasoning_trace = []

        # Execute reasoning display first
        for step in plan.reasoning_steps:
            reasoning_trace.append(f"[{step.type}] {step.description}")

        # Execute tool calls
        for tool_call in plan.tool_calls:
            result = await self._execute_tool(tool_call.tool_name, tool_call.arguments)
            tool_results.append(result)

            if not result.success:
                reasoning_trace.append(f"⚠️ {tool_call.tool_name} failed: {result.error}")

        # Synthesize response
        final_response = self._synthesize_response(plan, tool_results)

        return ActionResult(
            tool_results=tool_results,
            final_response=final_response,
            reasoning_trace=reasoning_trace,
            success=all(r.success for r in tool_results)
        )

    async def _execute_tool(self, tool_name: str, arguments: Dict) -> ToolResult:
        """Execute single MCP tool.

        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments

        Returns:
            ToolResult with outcome
        """
        import time
        start = time.time()

        try:
            # Call MCP tool
            result = await self.session.call_tool(tool_name, arguments)

            execution_time = (time.time() - start) * 1000

            return ToolResult(
                tool_name=tool_name,
                success=True,
                data=result.content,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = (time.time() - start) * 1000

            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )

    def _synthesize_response(
        self,
        plan: DecisionPlan,
        tool_results: List[ToolResult]
    ) -> str:
        """Create natural language response.

        Args:
            plan: Original plan
            tool_results: Results from tool execution

        Returns:
            Natural language response
        """
        # If plan has final answer, use it
        if plan.final_answer:
            return plan.final_answer

        # Otherwise, synthesize from tool results
        successful_results = [r for r in tool_results if r.success]

        if not successful_results:
            return "I apologize, but I encountered an error processing your request. Could you rephrase?"

        # Extract data from search_shops
        for result in successful_results:
            if result.tool_name == "search_shops" and result.data:
                # Parse shop results
                shops_text = str(result.data)

                # Simple extraction (in real implementation, parse JSON)
                return f"I found the following options for you:\n\n{shops_text}\n\nWould you like more details about any of these?"

            elif result.tool_name == "get_shop_details" and result.data:
                return f"Here are the details:\n\n{result.data}"

            elif result.tool_name == "calculate_route" and result.data:
                return f"I've calculated an efficient route for you:\n\n{result.data}"

            elif result.tool_name == "get_mall_facilities" and result.data:
                return f"Mall facilities:\n\n{result.data}"

        return "I've processed your request. How else can I help?"

    async def execute_parallel(self, tool_calls: List) -> List[ToolResult]:
        """Execute multiple tools in parallel.

        Args:
            tool_calls: List of tool calls to execute

        Returns:
            List of ToolResults
        """
        tasks = [
            self._execute_tool(call.tool_name, call.arguments)
            for call in tool_calls
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed ToolResults
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ToolResult(
                    tool_name=tool_calls[i].tool_name,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        return final_results
