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
import json
from layer_logger import LayerLogger


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
        # Log layer start
        LayerLogger.log_layer_start("Action", 4)

        # Log input
        LayerLogger.log_input(plan, "Action Plan")

        tool_results = []
        reasoning_trace = []

        # Execute reasoning display first
        for step in plan.reasoning_steps:
            reasoning_trace.append(f"[{step.type}] {step.description}")

        LayerLogger.log_summary("Reasoning Steps", reasoning_trace)

        # Execute tool calls
        LayerLogger.log_processing(f"Executing {len(plan.tool_calls)} tool calls")

        for tool_call in plan.tool_calls:
            LayerLogger.log_tool_call(tool_call.tool_name, tool_call.arguments)

            result = await self._execute_tool(tool_call.tool_name, tool_call.arguments)
            tool_results.append(result)

            LayerLogger.log_tool_result(tool_call.tool_name, result.success, result.execution_time_ms)

            if not result.success:
                reasoning_trace.append(f"⚠️ {tool_call.tool_name} failed: {result.error}")

        # Synthesize response
        LayerLogger.log_processing("Synthesizing human-readable response from tool results")

        final_response = self._synthesize_response(plan, tool_results)

        action_result = ActionResult(
            tool_results=tool_results,
            final_response=final_response,
            reasoning_trace=reasoning_trace,
            success=all(r.success for r in tool_results)
        )

        # Log output
        LayerLogger.log_output({
            "success": action_result.success,
            "tools_executed": len(tool_results),
            "response_preview": final_response[:200] + "..." if len(final_response) > 200 else final_response
        }, "Action Result")

        return action_result

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

    def _extract_text_from_content(self, content_list) -> str:
        """Extract text from MCP TextContent list.

        Args:
            content_list: List of TextContent objects from MCP

        Returns:
            Extracted text string
        """
        if not content_list:
            return ""

        # MCP returns list of TextContent objects
        if isinstance(content_list, list) and len(content_list) > 0:
            # Access the text attribute of first TextContent
            first_item = content_list[0]
            if hasattr(first_item, 'text'):
                return first_item.text

        # Fallback
        return str(content_list)

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

        # Process each tool result
        for result in successful_results:
            if result.tool_name == "search_shops" and result.data:
                # Extract text from TextContent
                raw_text = self._extract_text_from_content(result.data)

                try:
                    # Parse JSON shop data
                    shops = json.loads(raw_text)

                    # Format human-readable response
                    if not shops:
                        return "I couldn't find any shops matching your criteria. Would you like to adjust your search?"

                    response_parts = ["I found the following options for you:\n"]

                    for i, shop in enumerate(shops[:5], 1):  # Limit to 5 shops
                        response_parts.append(
                            f"{i}. **{shop['name']}** ({shop['category']}) - Floor {shop['floor']}\n"
                            f"   {shop['description']}\n"
                            f"   Price range: {shop.get('price_range', 'N/A')}"
                        )

                        # Add rating if available
                        if 'rating' in shop:
                            response_parts[-1] += f" | Rating: {shop['rating']}/5.0"

                        response_parts[-1] += "\n"

                    if len(shops) > 5:
                        response_parts.append(f"\n...and {len(shops) - 5} more options available.")

                    response_parts.append("\nWould you like more details about any specific shop?")
                    return "\n".join(response_parts)

                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return f"I found some options:\n\n{raw_text}\n\nWould you like more details?"

            elif result.tool_name == "get_shop_details" and result.data:
                raw_text = self._extract_text_from_content(result.data)

                try:
                    shop = json.loads(raw_text)
                    response = f"**{shop['name']}**\n"
                    response += f"📍 Location: Floor {shop['floor']}\n"

                    if 'hours' in shop:
                        response += f"🕐 Hours: {shop['hours']}\n"
                    if 'price_range' in shop:
                        response += f"💰 Price Range: {shop['price_range']}\n"
                    if 'rating' in shop:
                        response += f"⭐ Rating: {shop['rating']}/5.0\n"

                    response += f"\n{shop.get('description', '')}\n"

                    if 'specialties' in shop and shop['specialties']:
                        response += f"\nSpecialties: {', '.join(shop['specialties'])}"

                    return response
                except json.JSONDecodeError:
                    return f"Here are the details:\n\n{raw_text}"

            elif result.tool_name == "calculate_route" and result.data:
                raw_text = self._extract_text_from_content(result.data)

                try:
                    route = json.loads(raw_text)
                    response_parts = ["I've planned an efficient route for you:\n"]

                    total_time = route.get('total_time_minutes', 0)
                    total_distance = route.get('total_distance_meters', 0)

                    response_parts.append(f"⏱️  Estimated time: {total_time} minutes")
                    response_parts.append(f"📏 Total distance: {total_distance}m\n")
                    response_parts.append("Route:")

                    for i, stop in enumerate(route.get('stops', []), 1):
                        response_parts.append(f"{i}. {stop.get('shop_name', 'Unknown')} (Floor {stop.get('floor', '?')})")

                    return "\n".join(response_parts)
                except json.JSONDecodeError:
                    return f"Here's your route:\n\n{raw_text}"

            elif result.tool_name == "get_mall_facilities" and result.data:
                raw_text = self._extract_text_from_content(result.data)
                return f"Mall Facilities:\n\n{raw_text}"

            elif result.tool_name == "get_recommendations" and result.data:
                raw_text = self._extract_text_from_content(result.data)

                try:
                    recommendations = json.loads(raw_text)
                    if isinstance(recommendations, list):
                        response_parts = ["Here are my personalized recommendations for you:\n"]

                        for i, shop in enumerate(recommendations[:5], 1):
                            response_parts.append(
                                f"{i}. **{shop['name']}** ({shop.get('category', 'N/A')}) - Floor {shop.get('floor', '?')}\n"
                                f"   {shop.get('description', '')}\n"
                                f"   {shop.get('recommendation_reason', '')}\n"
                            )

                        return "\n".join(response_parts)
                except json.JSONDecodeError:
                    pass

                return f"Recommendations:\n\n{raw_text}"

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
