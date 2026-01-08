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

    def _aggregate_tool_results(self, results: List[ToolResult]) -> Dict[str, Any]:
        """Aggregate ALL 14 tool results into structured data.

        Collects data from all available mall tools:
        - Core: search_shops, get_shop_details, calculate_route, verify_route
        - Recommendations: get_recommendations
        - Info: check_shop_hours, get_accessibility_info, check_wait_time
        - Facilities: get_mall_facilities, get_current_events
        - Accessibility: calculate_accessible_route
        - Reasoning: show_reasoning
        - Lost & Found: search_lost_and_found, log_lost_item

        Args:
            results: List of ToolResult objects from tool execution

        Returns:
            Dict with aggregated data from all tools:
            {
                'shops': List[Dict],  # From search_shops
                'shop_details': List[Dict],  # From get_shop_details
                'route': Optional[Dict],  # From calculate_route or calculate_accessible_route
                'route_verified': Optional[bool],  # From verify_route
                'accessibility': Dict[str, Any],  # From get_accessibility_info
                'recommendations': List[Dict],  # From get_recommendations
                'shop_hours': List[Dict],  # From check_shop_hours
                'facilities': List[Dict],  # From get_mall_facilities
                'events': List[Dict],  # From get_current_events
                'wait_times': List[Dict],  # From check_wait_time
                'reasoning': List[str],  # From show_reasoning
                'lost_found': List[Dict]  # From search_lost_and_found
            }
        """
        aggregated = {
            'shops': [],
            'shop_details': [],
            'route': None,
            'route_verified': None,
            'accessibility': {},
            'recommendations': [],
            'shop_hours': [],
            'facilities': [],
            'events': [],
            'wait_times': [],
            'reasoning': [],
            'lost_found': []
        }

        for result in results:
            if not result.success:
                continue

            raw_text = self._extract_text_from_content(result.data)

            try:
                if result.tool_name == "search_shops":
                    shops = json.loads(raw_text)
                    if isinstance(shops, list):
                        aggregated['shops'].extend(shops)

                elif result.tool_name == "get_shop_details":
                    details = json.loads(raw_text)
                    aggregated['shop_details'].append(details)

                elif result.tool_name in ["calculate_route", "calculate_accessible_route"]:
                    aggregated['route'] = json.loads(raw_text)

                elif result.tool_name == "verify_route":
                    verification = json.loads(raw_text)
                    aggregated['route_verified'] = verification.get('verified', False)

                elif result.tool_name == "get_accessibility_info":
                    access_info = json.loads(raw_text)
                    shop_name = access_info.get('shop_name')
                    if shop_name:
                        aggregated['accessibility'][shop_name] = access_info

                elif result.tool_name == "get_recommendations":
                    recs = json.loads(raw_text)
                    if isinstance(recs, list):
                        aggregated['recommendations'].extend(recs)

                elif result.tool_name == "check_shop_hours":
                    hours = json.loads(raw_text)
                    aggregated['shop_hours'].append(hours)

                elif result.tool_name == "get_mall_facilities":
                    facilities = json.loads(raw_text)
                    if isinstance(facilities, list):
                        aggregated['facilities'].extend(facilities)

                elif result.tool_name == "get_current_events":
                    events = json.loads(raw_text)
                    if isinstance(events, list):
                        aggregated['events'].extend(events)

                elif result.tool_name == "check_wait_time":
                    wait_time = json.loads(raw_text)
                    aggregated['wait_times'].append(wait_time)

                elif result.tool_name == "show_reasoning":
                    reasoning = json.loads(raw_text)
                    if 'steps' in reasoning:
                        aggregated['reasoning'] = reasoning['steps']

                elif result.tool_name == "search_lost_and_found":
                    lost_items = json.loads(raw_text)
                    if isinstance(lost_items, list):
                        aggregated['lost_found'].extend(lost_items)

            except json.JSONDecodeError:
                # Skip malformed JSON
                continue

        # Deduplicate shops by ID
        if aggregated['shops']:
            unique_shops = {shop['id']: shop for shop in aggregated['shops'] if 'id' in shop}
            aggregated['shops'] = list(unique_shops.values())

        return aggregated

    def _extract_time_constraint(self, plan: DecisionPlan) -> Optional[int]:
        """Extract time constraint from plan reasoning steps.

        Looks for time mentions in reasoning steps like:
        - "4-5 hours"
        - "3 hours max"
        - "240 minutes"

        Args:
            plan: DecisionPlan with reasoning steps

        Returns:
            Time in minutes or None if no constraint found
        """
        import re

        for step in plan.reasoning_steps:
            desc = step.description.lower()

            # Pattern 1: "X hours" or "X-Y hours"
            hours_match = re.search(r'(\d+)(?:-(\d+))?\s*hours?', desc)
            if hours_match:
                # Use the higher bound if range given
                hours = int(hours_match.group(2) or hours_match.group(1))
                return hours * 60

            # Pattern 2: "X minutes"
            minutes_match = re.search(r'(\d+)\s*min(?:ute)?s?', desc)
            if minutes_match:
                return int(minutes_match.group(1))

        return None

    def _extract_occasion_context(self, plan: DecisionPlan) -> Optional[str]:
        """Extract occasion context (birthday, anniversary, etc.) from plan reasoning.

        Args:
            plan: DecisionPlan with reasoning steps

        Returns:
            Occasion description or None
        """
        # Check reasoning steps and entities for occasion keywords
        occasion_keywords = {
            'birthday': 'birthday celebration',
            'anniversary': 'anniversary',
            'celebration': 'special celebration',
            'party': 'party',
            'graduation': 'graduation',
            'valentine': "Valentine's Day"
        }

        for step in plan.reasoning_steps:
            desc = step.description.lower()
            for keyword, occasion in occasion_keywords.items():
                if keyword in desc:
                    return occasion

        return None

    def _create_personalized_greeting(
        self,
        plan: DecisionPlan,
        shops: List[Dict],
        time_constraint: Optional[int] = None
    ) -> str:
        """Create a personalized greeting based on the user's context.

        Analyzes reasoning steps to extract:
        - Occasion (birthday, anniversary, etc.)
        - Group composition (family, couple, solo, friends)
        - Purpose (shopping, dining, entertainment, gifts)
        - Time available

        Args:
            plan: DecisionPlan with reasoning steps
            shops: List of shops in itinerary
            time_constraint: Time available in minutes

        Returns:
            Personalized greeting message
        """
        # Extract context from reasoning steps
        reasoning_text = " ".join([step.description.lower() for step in plan.reasoning_steps])

        # Detect occasion
        occasion = None
        occasion_keywords = {
            'birthday': ('🎂', "Happy Birthday planning!"),
            'anniversary': ('💑', "Happy Anniversary planning!"),
            'graduation': ('🎓', "Congratulations on the graduation!"),
            'valentine': ('💝', "Happy Valentine's Day!"),
            'wedding': ('💍', "Congratulations on your upcoming wedding!"),
            'celebration': ('🎉', "Happy celebration planning!")
        }

        for keyword, (emoji, message) in occasion_keywords.items():
            if keyword in reasoning_text:
                occasion = (emoji, message)
                break

        # Detect group composition
        group_context = None
        if 'family' in reasoning_text:
            if any(word in reasoning_text for word in ['daughter', 'son', 'child', 'kid']):
                group_context = "with your family"
            else:
                group_context = "with your loved ones"
        elif 'couple' in reasoning_text or 'romantic' in reasoning_text:
            group_context = "for a romantic outing"
        elif 'friend' in reasoning_text:
            group_context = "with friends"

        # Detect group size
        group_size = None
        import re
        size_match = re.search(r'(?:family|group).*?of\s+(\d+)', reasoning_text)
        if size_match:
            group_size = int(size_match.group(1))

        # Categorize shops
        categories = [shop.get('category', '') for shop in shops]
        has_toys = any('toy' in cat.lower() for cat in categories)
        has_food = any('food' in cat.lower() or 'restaurant' in cat.lower() for cat in categories)
        has_jewelry = any('jewel' in cat.lower() for cat in categories)
        has_fashion = any('fashion' in cat.lower() or 'clothing' in cat.lower() for cat in categories)

        # Build personalized greeting
        parts = []

        if occasion:
            emoji, message = occasion
            parts.append(f"{emoji} {message}")

        # Add context-aware message
        if 'birthday' in reasoning_text and 'daughter' in reasoning_text:
            parts.append("I've planned a wonderful day to celebrate your daughter's special day!")
        elif 'birthday' in reasoning_text and 'child' in reasoning_text:
            parts.append("I've planned an exciting birthday adventure!")
        elif occasion and group_context:
            parts.append(f"I've crafted a special itinerary {group_context}!")
        elif group_context:
            parts.append(f"I've planned a great mall experience {group_context}!")
        else:
            parts.append("I've created a personalized itinerary just for you!")

        # Add details about what's included
        activity_parts = []
        if has_toys and has_food:
            activity_parts.append("combining fun shopping and delicious dining")
        elif has_jewelry and has_food:
            activity_parts.append("blending special gift shopping with fine dining")
        elif has_fashion and has_food:
            activity_parts.append("mixing fashion browsing with great food")
        elif has_toys:
            activity_parts.append("featuring exciting toy stores")
        elif has_food:
            activity_parts.append("highlighting excellent dining options")

        if group_size:
            activity_parts.append(f"perfect for a group of {group_size}")

        if time_constraint:
            hours = time_constraint // 60
            mins = time_constraint % 60
            if mins > 0:
                activity_parts.append(f"optimized for your {hours}h {mins}min timeframe")
            else:
                activity_parts.append(f"optimized for your {hours}-hour timeframe")

        if activity_parts:
            parts.append(" ".join(activity_parts).capitalize() + ".")

        return " ".join(parts)

    def _calculate_time_allocations(
        self,
        shops: List[Dict],
        total_time_minutes: Optional[int]
    ) -> Dict[int, Dict]:
        """Calculate time allocation for each shop visit.

        Distributes time across shops based on:
        - Category (Food gets more time than accessories)
        - User's total time constraint (uses FULL time, no rushing)
        - Number of shops to visit

        Args:
            shops: List of shop dictionaries
            total_time_minutes: Max time in minutes from user query

        Returns:
            Dict mapping shop_id to time allocation:
            {shop_id: {'duration': int, 'start': str, 'end': str}}
        """
        from datetime import datetime, timedelta

        # Category-based default time allocations (in minutes)
        category_times = {
            'Food': 60,  # Dining takes time
            'Jewelry': 35,  # Browsing + selection
            'Fashion': 30,
            'Toys': 25,
            'Electronics': 20,
            'Books': 20,
            'Home & Garden': 25,
            'Sports & Outdoors': 20,
            'Health & Beauty': 25
        }

        allocations = {}
        current_time = datetime.now()  # Use actual current time, not hardcoded 2 PM

        # Calculate total needed time
        total_needed = sum(category_times.get(shop.get('category'), 25) for shop in shops)

        # Scale factor - use FULL time available, don't rush
        scale_factor = 1.0
        if total_time_minutes:
            # If user gave time constraint, use it fully (don't finish early)
            # Scale up or down to use the full time available
            scale_factor = total_time_minutes / total_needed if total_needed > 0 else 1.0

        for shop in shops:
            shop_id = shop.get('id')
            if not shop_id:
                continue

            # Get base duration for category
            base_duration = category_times.get(shop.get('category'), 25)

            # Apply scaling to use full available time
            duration = int(base_duration * scale_factor)
            duration = max(duration, 15)  # Minimum 15 minutes per stop (comfortable browsing)

            # Calculate start and end times
            start_time = current_time
            end_time = current_time + timedelta(minutes=duration)

            allocations[shop_id] = {
                'duration': duration,
                'start': start_time.strftime('%I:%M %p'),
                'end': end_time.strftime('%I:%M %p')
            }

            # Move to next time slot (duration + 5 min walking time)
            current_time += timedelta(minutes=duration + 5)

        return allocations

    def _create_detailed_itinerary(
        self,
        aggregated_data: Dict[str, Any],
        user_time_constraint: Optional[int] = None,
        plan: Optional[DecisionPlan] = None
    ) -> str:
        """Create comprehensive itinerary using ALL aggregated tool data.

        Incorporates data from multiple tool types:
        - Shops from search_shops
        - Recommendations from get_recommendations
        - Route from calculate_route/calculate_accessible_route
        - Route verification from verify_route
        - Accessibility info from get_accessibility_info
        - Shop hours from check_shop_hours
        - Wait times from check_wait_time
        - Current events from get_current_events
        - Nearby facilities from get_mall_facilities

        Args:
            aggregated_data: Dict with all tool results
            user_time_constraint: Max time in minutes from user query
            plan: Optional DecisionPlan to extract context from

        Returns:
            Formatted itinerary string with STOP-by-STOP details
        """
        shops = aggregated_data.get('shops', [])
        recommendations = aggregated_data.get('recommendations', [])
        route = aggregated_data.get('route')
        route_verified = aggregated_data.get('route_verified')
        accessibility = aggregated_data.get('accessibility', {})
        shop_hours_list = aggregated_data.get('shop_hours', [])
        wait_times = aggregated_data.get('wait_times', [])
        events = aggregated_data.get('events', [])
        facilities = aggregated_data.get('facilities', [])

        # Combine shops and recommendations (recommendations often have better context)
        all_stops = shops[:]
        for rec in recommendations:
            if 'id' in rec and rec['id'] not in [s.get('id') for s in all_stops]:
                all_stops.append(rec)

        if not all_stops:
            return "I couldn't find any shops matching your criteria. Would you like to adjust your search?"

        # Calculate time allocations
        time_allocs = self._calculate_time_allocations(all_stops, user_time_constraint)

        # Build itinerary
        lines = []

        # Add personalized greeting based on context
        if plan:
            greeting = self._create_personalized_greeting(plan, all_stops, user_time_constraint)
            if greeting:
                lines.append(greeting)
                lines.append("")

        lines.append("🛍️ YOUR PERSONALIZED MALL ITINERARY\n")

        # Overview section
        total_duration = sum(ta['duration'] for ta in time_allocs.values())
        floors = sorted(set(shop.get('floor', 1) for shop in all_stops))

        lines.append("📋 Overview:")
        lines.append(f"• Total Stops: {len(all_stops)}")
        lines.append(f"• Estimated Duration: {total_duration // 60} hours {total_duration % 60} minutes")
        lines.append(f"• Floors Visited: {', '.join(map(str, floors))}")

        if route:
            distance = route.get('total_distance_meters', 0)
            lines.append(f"• Total Walking Distance: {distance}m")

        if route_verified:
            lines.append("• ✓ Route Verified - Meets all your constraints")

        lines.append("\n" + "━" * 60 + "\n")

        # Individual stop details
        for i, shop in enumerate(all_stops, 1):
            shop_id = shop.get('id')
            time_alloc = time_allocs.get(shop_id, {})
            shop_name = shop.get('name', 'Unknown Shop')

            # Stop header
            lines.append(f"STOP {i}: {shop_name} (Floor {shop.get('floor', '?')})")

            # Time allocation
            duration = time_alloc.get('duration', 30)
            start = time_alloc.get('start', 'TBD')
            end = time_alloc.get('end', 'TBD')
            lines.append(f"⏱️  Time: {duration} minutes ({start} - {end})")

            # Location
            lines.append(f"📍 Location: Floor {shop.get('floor', '?')}")

            # Price and rating
            if 'price_range' in shop:
                lines.append(f"💰 Price Range: {shop['price_range']}")
            if 'rating' in shop:
                lines.append(f"⭐ Rating: {shop['rating']}/5.0")

            # Description
            if 'description' in shop:
                lines.append(f"📝 {shop['description']}")

            # Shop hours (if available)
            shop_hours = next((h for h in shop_hours_list if h.get('shop_name') == shop_name), None)
            if shop_hours:
                if shop_hours.get('is_open'):
                    lines.append(f"🕐 OPEN NOW (Closes at {shop_hours.get('closing_time', 'Unknown')})")
                else:
                    lines.append(f"🕐 Currently Closed")

            # Wait time info
            wait_info = next((w for w in wait_times if w.get('location_name') == shop_name), None)
            if wait_info:
                crowd_level = wait_info.get('crowd_level', 'Unknown')
                wait_mins = wait_info.get('estimated_wait_minutes', 0)
                if wait_mins > 0:
                    lines.append(f"👥 Wait Time: {crowd_level} (~{wait_mins} minutes)")
                else:
                    lines.append(f"👥 Crowd Level: {crowd_level}")

            # Events at this shop
            shop_events = [e for e in events if shop_name.lower() in e.get('location', '').lower()]
            if shop_events:
                for event in shop_events:
                    lines.append(f"🎉 SPECIAL: {event.get('title', 'Event')}")

            # Accessibility information
            access_info = accessibility.get(shop_name)
            if access_info:
                lines.append("\n♿ Accessibility:")
                if access_info.get('wheelchair_accessible'):
                    lines.append("   • Wheelchair accessible entrance")
                if 'elevator_distance' in access_info:
                    lines.append(f"   • Elevator {access_info['elevator_distance']}m away")
                if access_info.get('rest_area_nearby'):
                    lines.append("   • Rest area nearby")
                if access_info.get('accessible_parking'):
                    lines.append("   • Accessible parking available")

            # Nearby facilities
            if facilities:
                lines.append("\n🚻 Nearby Facilities:")
                for facility in facilities[:3]:  # Show up to 3 facilities
                    fac_name = facility.get('name', 'Unknown')
                    fac_floor = facility.get('floor', '?')
                    lines.append(f"   • {fac_name} (Floor {fac_floor})")

            lines.append("\n" + "━" * 60 + "\n")

        # Route summary
        if route and 'stops' in route:
            lines.append("📊 ROUTE SUMMARY:")
            stop_names = [s.get('shop_name', 'Unknown') for s in route['stops']]
            route_str = " → ".join(stop_names)
            lines.append(f"   {route_str}\n")

        return "\n".join(lines)

    def _format_shop_details(self, shop: Dict) -> str:
        """Format single shop details (for get_shop_details tool)."""
        lines = [f"**{shop.get('name', 'Unknown Shop')}**"]
        lines.append(f"📍 Location: Floor {shop.get('floor', '?')}")

        if 'hours' in shop:
            lines.append(f"🕐 Hours: {shop['hours']}")
        if 'price_range' in shop:
            lines.append(f"💰 Price Range: {shop['price_range']}")
        if 'rating' in shop:
            lines.append(f"⭐ Rating: {shop['rating']}/5.0")
        if 'description' in shop:
            lines.append(f"\n{shop['description']}")
        if 'specialties' in shop and shop.get('specialties'):
            lines.append(f"\nSpecialties: {', '.join(shop['specialties'])}")

        return "\n".join(lines)

    def _format_route(self, route: Dict, verified: Optional[bool] = None) -> str:
        """Format route with optional verification status."""
        lines = ["I've planned an efficient route for you:\n"]

        if verified:
            lines.append("✓ Route Verified - Meets all your constraints\n")

        if 'total_time_minutes' in route:
            lines.append(f"⏱️  Estimated time: {route['total_time_minutes']} minutes")
        if 'total_distance_meters' in route:
            lines.append(f"📏 Total distance: {route['total_distance_meters']}m\n")

        if 'stops' in route:
            lines.append("Route:")
            for i, stop in enumerate(route['stops'], 1):
                lines.append(f"{i}. {stop.get('shop_name', 'Unknown')} (Floor {stop.get('floor', '?')})")

        return "\n".join(lines)

    def _format_facilities(self, facilities: List[Dict]) -> str:
        """Format mall facilities list."""
        lines = ["🏢 Mall Facilities:\n"]
        for facility in facilities:
            lines.append(f"• **{facility.get('name', 'Unknown')}** - Floor {facility.get('floor', '?')}")
            if 'location_description' in facility:
                lines.append(f"  {facility['location_description']}")
        return "\n".join(lines)

    def _format_events(self, events: List[Dict]) -> str:
        """Format current events/promotions."""
        lines = ["🎉 Current Events & Promotions:\n"]
        for event in events:
            lines.append(f"• **{event.get('title', 'Event')}**")
            if 'description' in event:
                lines.append(f"  {event['description']}")
            if 'location' in event:
                lines.append(f"  📍 {event['location']}")
            if 'end_date' in event:
                lines.append(f"  ⏰ Until {event['end_date']}")
            lines.append("")
        return "\n".join(lines)

    def _format_lost_and_found(self, items: List[Dict]) -> str:
        """Format lost and found items."""
        lines = ["🔍 Lost & Found Items:\n"]
        for item in items:
            lines.append(f"• **{item.get('item_type', 'Item')}**")
            if 'description' in item:
                lines.append(f"  {item['description']}")
            if 'found_location' in item:
                lines.append(f"  Found at: {item['found_location']}")
            if 'claim_location' in item:
                lines.append(f"  Claim at: {item['claim_location']}")
            lines.append("")
        return "\n".join(lines)

    def _format_wait_times(self, wait_times: List[Dict]) -> str:
        """Format wait time information."""
        lines = ["⏰ Current Wait Times:\n"]
        for wt in wait_times:
            location = wt.get('location_name', 'Unknown')
            status = wt.get('crowd_level', 'Unknown')
            wait = wt.get('estimated_wait_minutes', 0)

            lines.append(f"• **{location}**")
            lines.append(f"  Status: {status}")
            if wait > 0:
                lines.append(f"  Wait time: ~{wait} minutes")
            lines.append("")
        return "\n".join(lines)

    def _synthesize_response(
        self,
        plan: DecisionPlan,
        tool_results: List[ToolResult]
    ) -> str:
        """Create natural language response from tool results.

        AGGREGATES ALL 14 tool types before formatting to avoid early-return
        anti-pattern that loses data from subsequent tool calls.

        Args:
            plan: Original decision plan
            tool_results: Results from tool execution

        Returns:
            Natural language response (itinerary, shop details, facilities, etc.)
        """
        # If plan has final answer, use it
        if plan.final_answer:
            return plan.final_answer

        # Filter successful results
        successful_results = [r for r in tool_results if r.success]

        if not successful_results:
            return "I apologize, but I encountered an error processing your request. Could you rephrase?"

        # PHASE 1: Aggregate all tool data (all 14 types)
        aggregated = self._aggregate_tool_results(successful_results)

        # PHASE 2: Determine response type based on available data

        # Case 1: Multi-shop itinerary (most common - shopping plans)
        if aggregated['shops'] or aggregated['recommendations']:
            time_constraint = self._extract_time_constraint(plan)
            return self._create_detailed_itinerary(
                aggregated_data=aggregated,
                user_time_constraint=time_constraint,
                plan=plan  # Pass plan for personalized greeting
            )

        # Case 2: Single shop details query
        if aggregated['shop_details']:
            return self._format_shop_details(aggregated['shop_details'][0])

        # Case 3: Route-only query
        if aggregated['route']:
            return self._format_route(aggregated['route'], aggregated.get('route_verified'))

        # Case 4: Facilities query
        if aggregated['facilities']:
            return self._format_facilities(aggregated['facilities'])

        # Case 5: Events query
        if aggregated['events']:
            return self._format_events(aggregated['events'])

        # Case 6: Lost & found query
        if aggregated['lost_found']:
            return self._format_lost_and_found(aggregated['lost_found'])

        # Case 7: Wait times query
        if aggregated['wait_times']:
            return self._format_wait_times(aggregated['wait_times'])

        # Final fallback if no structured data matched
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
