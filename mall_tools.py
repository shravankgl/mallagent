from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import logging
from rich.logging import RichHandler
import json
from typing import List, Dict, Optional
from datetime import datetime

# Configure logging with Rich handler for colored, formatted output to file
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            console=__import__('rich.console').console.Console(file=open('mall_server.log', 'a'))
        )
    ]
)
logger = logging.getLogger(__name__)

mcp = FastMCP("MallAssistant")

# Load mall data
with open('mall_data.json', 'r') as f:
    MALL_DATA = json.load(f)

@mcp.tool()
def show_reasoning(steps: list) -> TextContent:
    """Display the step-by-step reasoning process for mall assistance"""
    logger.info("[blue]FUNCTION CALL:[/blue] show_reasoning()")
    for i, step in enumerate(steps, 1):
        logger.info(f"[cyan]Step {i}:[/cyan] {step}")
    return TextContent(
        type="text",
        text=f"Reasoning displayed: {len(steps)} steps"
    )

@mcp.tool()
def search_shops(category: Optional[str] = None, floor: Optional[int] = None, keyword: Optional[str] = None) -> TextContent:
    """
    Search for shops in the mall by category, floor, or keyword

    Args:
        category: Shop category (e.g., "Fashion", "Food", "Electronics")
        floor: Floor number (1-5)
        keyword: Search keyword in shop name or description
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] search_shops(category={category}, floor={floor}, keyword={keyword})")

    results = []
    for shop in MALL_DATA["shops"]:
        match = True

        if category and shop["category"].lower() != category.lower():
            match = False

        if floor and shop["floor"] != floor:
            match = False

        if keyword:
            keyword_lower = keyword.lower()
            if not (keyword_lower in shop["name"].lower() or
                   keyword_lower in shop["description"].lower() or
                   keyword_lower in shop["category"].lower()):
                match = False

        if match:
            results.append(shop)

    logger.info(f"[green]Found {len(results)} shops[/green]")
    return TextContent(
        type="text",
        text=json.dumps(results, indent=2)
    )

@mcp.tool()
def get_shop_details(shop_name: str) -> TextContent:
    """
    Get detailed information about a specific shop

    Args:
        shop_name: Name of the shop
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] get_shop_details(shop_name={shop_name})")

    for shop in MALL_DATA["shops"]:
        if shop["name"].lower() == shop_name.lower():
            logger.info(f"[green]Found shop: {shop['name']}[/green]")
            return TextContent(
                type="text",
                text=json.dumps(shop, indent=2)
            )

    logger.warning(f"[yellow]Shop not found: {shop_name}[/yellow]")
    return TextContent(
        type="text",
        text=json.dumps({"error": f"Shop '{shop_name}' not found"})
    )

@mcp.tool()
def calculate_route(shop_ids: list) -> TextContent:
    """
    Calculate an optimized route through multiple shops
    Minimizes floor changes and provides efficient visiting order

    Args:
        shop_ids: List of shop IDs to visit
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] calculate_route(shop_ids={shop_ids})")

    # Get shop details
    shops = []
    for shop_id in shop_ids:
        for shop in MALL_DATA["shops"]:
            if shop["id"] == shop_id:
                shops.append(shop)
                break

    if not shops:
        return TextContent(
            type="text",
            text=json.dumps({"error": "No valid shops found"})
        )

    # Sort by floor to minimize travel
    sorted_shops = sorted(shops, key=lambda x: x["floor"])

    # Calculate route info
    route = {
        "total_shops": len(sorted_shops),
        "floors_visited": sorted(list(set(s["floor"] for s in sorted_shops))),
        "floor_changes": len(set(s["floor"] for s in sorted_shops)) - 1,
        "optimized_order": [
            {
                "sequence": i + 1,
                "shop_name": shop["name"],
                "floor": shop["floor"],
                "category": shop["category"]
            }
            for i, shop in enumerate(sorted_shops)
        ],
        "estimated_time_minutes": len(sorted_shops) * 15 + len(set(s["floor"] for s in sorted_shops)) * 3
    }

    logger.info(f"[green]Route calculated: {len(sorted_shops)} shops across {len(route['floors_visited'])} floors[/green]")
    return TextContent(
        type="text",
        text=json.dumps(route, indent=2)
    )

@mcp.tool()
def verify_route(shop_ids: list, constraints: dict) -> TextContent:
    """
    Verify if a route meets specified constraints

    Args:
        shop_ids: List of shop IDs in the route
        constraints: Dictionary of constraints like {"max_floors": 3, "max_time_minutes": 60, "required_categories": ["Food"]}
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] verify_route(shop_ids={shop_ids}, constraints={constraints})")

    # Get shops
    shops = [s for s in MALL_DATA["shops"] if s["id"] in shop_ids]

    if not shops:
        return TextContent(
            type="text",
            text=json.dumps({"verified": False, "error": "No valid shops"})
        )

    floors = set(s["floor"] for s in shops)
    categories = set(s["category"] for s in shops)
    estimated_time = len(shops) * 15 + len(floors) * 3

    verification = {
        "verified": True,
        "checks": []
    }

    # Check max floors
    if "max_floors" in constraints:
        max_floors_ok = len(floors) <= constraints["max_floors"]
        verification["checks"].append({
            "constraint": "max_floors",
            "required": constraints["max_floors"],
            "actual": len(floors),
            "passed": max_floors_ok
        })
        if not max_floors_ok:
            verification["verified"] = False

    # Check max time
    if "max_time_minutes" in constraints:
        max_time_ok = estimated_time <= constraints["max_time_minutes"]
        verification["checks"].append({
            "constraint": "max_time_minutes",
            "required": constraints["max_time_minutes"],
            "actual": estimated_time,
            "passed": max_time_ok
        })
        if not max_time_ok:
            verification["verified"] = False

    # Check required categories
    if "required_categories" in constraints:
        required_cats = set(constraints["required_categories"])
        has_all_cats = required_cats.issubset(categories)
        verification["checks"].append({
            "constraint": "required_categories",
            "required": list(required_cats),
            "actual": list(categories),
            "passed": has_all_cats
        })
        if not has_all_cats:
            verification["verified"] = False

    # Check accessibility (lower floors only)
    if "lower_floors_only" in constraints and constraints["lower_floors_only"]:
        max_floor = max(floors)
        lower_floors_ok = max_floor <= 2
        verification["checks"].append({
            "constraint": "lower_floors_only",
            "required": "Floors 1-2",
            "actual": f"Max floor {max_floor}",
            "passed": lower_floors_ok
        })
        if not lower_floors_ok:
            verification["verified"] = False

    status = "[green]✓ All constraints satisfied[/green]" if verification["verified"] else "[red]✗ Some constraints failed[/red]"
    logger.info(status)

    return TextContent(
        type="text",
        text=json.dumps(verification, indent=2)
    )

@mcp.tool()
def get_recommendations(context: str, preferences: Optional[dict] = None) -> TextContent:
    """
    Get context-aware shop recommendations

    Args:
        context: Context like "anniversary", "family_outing", "quick_lunch", "gift_shopping"
        preferences: Optional preferences like {"budget": "low", "interests": ["fashion", "books"]}
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] get_recommendations(context={context}, preferences={preferences})")

    recommendations = {
        "context": context,
        "suggested_shops": [],
        "suggested_route": []
    }

    # Context-based recommendations
    if context.lower() in ["anniversary", "romantic", "date"]:
        categories = ["Jewelry", "Fashion", "Food"]
        rec_text = "Romantic shopping experience"
    elif context.lower() in ["family", "family_outing"]:
        categories = ["Toys", "Food", "Entertainment"]
        rec_text = "Family-friendly activities"
    elif context.lower() in ["quick_lunch", "lunch", "food"]:
        categories = ["Food"]
        rec_text = "Dining options"
    elif context.lower() in ["gift", "gift_shopping"]:
        categories = ["Fashion", "Books", "Jewelry", "Beauty"]
        rec_text = "Gift shopping options"
    else:
        categories = list(set(s["category"] for s in MALL_DATA["shops"]))
        rec_text = "General recommendations"

    # Filter by preferences
    for shop in MALL_DATA["shops"]:
        if shop["category"] in categories:
            # Budget filter
            if preferences and "budget" in preferences:
                budget = preferences["budget"]
                if budget == "low" and "$$$" in shop["price_range"]:
                    continue
                elif budget == "high" and shop["price_range"] == "$":
                    continue

            recommendations["suggested_shops"].append({
                "name": shop["name"],
                "category": shop["category"],
                "floor": shop["floor"],
                "description": shop["description"],
                "hours": shop["hours"],
                "price_range": shop["price_range"]
            })

    recommendations["description"] = rec_text
    recommendations["total_recommendations"] = len(recommendations["suggested_shops"])

    logger.info(f"[green]Generated {len(recommendations['suggested_shops'])} recommendations[/green]")
    return TextContent(
        type="text",
        text=json.dumps(recommendations, indent=2)
    )

@mcp.tool()
def check_shop_hours(shop_name: str, current_time: Optional[str] = None) -> TextContent:
    """
    Check if a shop is currently open

    Args:
        shop_name: Name of the shop
        current_time: Time in "HH:MM AM/PM" format (optional, defaults to current time)
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] check_shop_hours(shop_name={shop_name}, current_time={current_time})")

    for shop in MALL_DATA["shops"]:
        if shop["name"].lower() == shop_name.lower():
            result = {
                "shop_name": shop["name"],
                "hours": shop["hours"],
                "floor": shop["floor"]
            }

            if current_time:
                # Simple check (would need proper time parsing in production)
                result["status"] = "Check shop hours: " + shop["hours"]
            else:
                result["status"] = "Shop hours: " + shop["hours"]

            logger.info(f"[green]Shop hours retrieved for {shop['name']}[/green]")
            return TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )

    return TextContent(
        type="text",
        text=json.dumps({"error": f"Shop '{shop_name}' not found"})
    )

@mcp.tool()
def get_mall_facilities(facility_type: Optional[str] = None) -> TextContent:
    """
    Get information about mall facilities like restrooms, ATMs, nursing rooms, etc.

    Args:
        facility_type: Type of facility (e.g., "restroom", "atm", "nursing_room", "parking", "elevator")
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] get_mall_facilities(facility_type={facility_type})")

    facilities = {
        "restrooms": [
            {"location": "Floor 1, Near Food Court", "accessible": True},
            {"location": "Floor 2, Near Cinema", "accessible": True},
            {"location": "Floor 3, East Wing", "accessible": True},
            {"location": "Floor 4, West Wing", "accessible": False},
            {"location": "Floor 5, Near Fitness Center", "accessible": True}
        ],
        "atm": [
            {"location": "Floor 1, Main Entrance", "bank": "Universal Bank"},
            {"location": "Floor 3, Food Court", "bank": "City Bank"}
        ],
        "nursing_room": [
            {"location": "Floor 1, Near Customer Service", "facilities": "Changing station, comfortable seating, privacy"},
            {"location": "Floor 3, Near Family Area", "facilities": "Changing station, comfortable seating, privacy"}
        ],
        "parking": {
            "levels": ["B1", "B2", "B3"],
            "total_spaces": 800,
            "accessible_spaces": 50,
            "ev_charging": "B1 - 10 stations"
        },
        "elevators": MALL_DATA["amenities"]["elevators"],
        "info_desk": "Ground Floor (Floor 1) - Main Entrance"
    }

    if facility_type:
        facility_type_lower = facility_type.lower().replace(" ", "_")
        if facility_type_lower in facilities:
            result = {facility_type: facilities[facility_type_lower]}
        else:
            result = {"error": f"Facility type '{facility_type}' not found", "available_types": list(facilities.keys())}
    else:
        result = facilities

    logger.info(f"[green]Facility information retrieved[/green]")
    return TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )

@mcp.tool()
def get_current_events() -> TextContent:
    """
    Get information about current mall events, promotions, and activities
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] get_current_events()")

    # Mock current events data
    events = {
        "ongoing_events": [
            {
                "name": "Holiday Shopping Festival",
                "location": "All Floors",
                "dates": "Dec 1 - Dec 31",
                "description": "Up to 50% off at participating stores",
                "featured_shops": ["Fashion Forward", "Tech Haven", "Jewelry Junction"]
            },
            {
                "name": "Kids Play Area",
                "location": "Floor 4, Near Kids Kingdom",
                "time": "10:00 AM - 8:00 PM daily",
                "description": "Free supervised play area for children 3-10 years",
                "cost": "Free"
            },
            {
                "name": "Live Music Weekend",
                "location": "Floor 3, Central Atrium",
                "time": "Saturdays & Sundays, 2:00 PM - 5:00 PM",
                "description": "Local artists performing live music",
                "cost": "Free"
            }
        ],
        "promotions": [
            {
                "title": "Dining Rewards",
                "description": "Spend $50+ at any restaurant, get $10 voucher for next visit",
                "valid_until": "End of month"
            },
            {
                "title": "First 100 Shoppers",
                "description": "Free gift bag on weekends (10 AM opening)",
                "location": "Main Entrance"
            }
        ],
        "upcoming": [
            {
                "name": "New Year's Eve Celebration",
                "date": "Dec 31, 8:00 PM",
                "location": "Floor 5, Rooftop",
                "description": "Countdown party with fireworks"
            }
        ]
    }

    logger.info(f"[green]Retrieved {len(events['ongoing_events'])} ongoing events[/green]")
    return TextContent(
        type="text",
        text=json.dumps(events, indent=2)
    )

@mcp.tool()
def get_accessibility_info(shop_name: str) -> TextContent:
    """
    Get accessibility information for a specific shop

    Args:
        shop_name: Name of the shop
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] get_accessibility_info(shop_name={shop_name})")

    for shop in MALL_DATA["shops"]:
        if shop["name"].lower() == shop_name.lower():
            # Generate accessibility info based on floor
            accessibility = {
                "shop_name": shop["name"],
                "floor": shop["floor"],
                "wheelchair_accessible": True,  # All shops are accessible
                "elevator_access": f"Elevators 1, 2, 3 serve Floor {shop['floor']}",
                "wide_aisles": shop["floor"] <= 3,  # Lower floors have wider aisles
                "accessible_entrance": True,
                "accessible_restroom_nearby": True,
                "distance_from_elevator": f"{(shop['id'] % 5 + 1) * 10} meters"
            }

            logger.info(f"[green]Accessibility info retrieved for {shop['name']}[/green]")
            return TextContent(
                type="text",
                text=json.dumps(accessibility, indent=2)
            )

    return TextContent(
        type="text",
        text=json.dumps({"error": f"Shop '{shop_name}' not found"})
    )

@mcp.tool()
def calculate_accessible_route(shop_ids: list) -> TextContent:
    """
    Calculate an accessible route that prioritizes elevator access and minimizes barriers

    Args:
        shop_ids: List of shop IDs to visit
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] calculate_accessible_route(shop_ids={shop_ids})")

    # Get shop details
    shops = [s for s in MALL_DATA["shops"] if s["id"] in shop_ids]

    if not shops:
        return TextContent(
            type="text",
            text=json.dumps({"error": "No valid shops found"})
        )

    # Sort by floor to minimize elevator use
    sorted_shops = sorted(shops, key=lambda x: x["floor"])

    accessible_route = {
        "total_shops": len(sorted_shops),
        "floors_visited": sorted(list(set(s["floor"] for s in sorted_shops))),
        "accessibility_features": {
            "elevator_only": True,
            "no_escalators": True,
            "wide_pathways": True,
            "rest_points": len(set(s["floor"] for s in sorted_shops))  # One per floor
        },
        "optimized_order": [
            {
                "sequence": i + 1,
                "shop_name": shop["name"],
                "floor": shop["floor"],
                "elevator_to_use": "Elevator 1 or 2",
                "accessible_entrance": "Yes",
                "rest_area_nearby": f"Floor {shop['floor']} seating area"
            }
            for i, shop in enumerate(sorted_shops)
        ],
        "estimated_time_minutes": len(sorted_shops) * 20 + len(set(s["floor"] for s in sorted_shops)) * 5,  # Extra time for accessibility
        "accessibility_notes": [
            "All routes use elevators only",
            "Wide aisles throughout the path",
            "Accessible restrooms on each floor",
            "Rest areas available every 50 meters"
        ]
    }

    logger.info(f"[green]Accessible route calculated: {len(sorted_shops)} shops[/green]")
    return TextContent(
        type="text",
        text=json.dumps(accessible_route, indent=2)
    )

@mcp.tool()
def check_wait_time(location_name: str) -> TextContent:
    """
    Check current wait times for restaurants, attractions, or services

    Args:
        location_name: Name of the location/shop
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] check_wait_time(location_name={location_name})")

    # Mock wait time data (in production, this would be real-time)
    import random
    random.seed(hash(location_name))  # Consistent results per location

    for shop in MALL_DATA["shops"]:
        if shop["name"].lower() == location_name.lower():
            # Generate realistic wait times based on category
            if shop["category"] == "Food":
                wait_minutes = random.randint(5, 30)
                crowd_level = "moderate" if wait_minutes < 15 else "busy"
            elif shop["category"] == "Entertainment":
                wait_minutes = random.randint(10, 45)
                crowd_level = "busy" if wait_minutes > 25 else "moderate"
            else:
                wait_minutes = random.randint(0, 10)
                crowd_level = "low"

            result = {
                "location": shop["name"],
                "current_wait_time_minutes": wait_minutes,
                "crowd_level": crowd_level,
                "last_updated": "2 minutes ago",
                "recommendation": "Good time to visit" if wait_minutes < 15 else "Consider visiting later" if wait_minutes > 30 else "Moderate wait expected"
            }

            logger.info(f"[green]Wait time: {wait_minutes} min for {shop['name']}[/green]")
            return TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )

    return TextContent(
        type="text",
        text=json.dumps({"error": f"Location '{location_name}' not found"})
    )

# In-memory lost & found storage (in production, use a database)
LOST_AND_FOUND = []

@mcp.tool()
def log_lost_item(description: str, location: str, contact_info: Optional[str] = None) -> TextContent:
    """
    Log a lost item to the mall's lost & found system

    Args:
        description: Description of the lost item
        location: Where the item was lost
        contact_info: Optional contact information for the person who lost the item
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] log_lost_item(description={description}, location={location})")

    from datetime import datetime

    item_id = len(LOST_AND_FOUND) + 1
    lost_item = {
        "item_id": item_id,
        "description": description,
        "location_lost": location,
        "date_logged": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "contact_info": contact_info if contact_info else "Not provided",
        "status": "Logged - Check back at Customer Service"
    }

    LOST_AND_FOUND.append(lost_item)

    logger.info(f"[green]Lost item logged with ID: {item_id}[/green]")
    return TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "item_id": item_id,
            "message": f"Item logged successfully. Please check at Customer Service (Floor 1) or call with reference ID: {item_id}",
            "item_details": lost_item
        }, indent=2)
    )

@mcp.tool()
def search_lost_and_found(item_type: str) -> TextContent:
    """
    Search the lost & found database for a specific type of item

    Args:
        item_type: Type of item (e.g., "phone", "wallet", "keys", "bag")
    """
    logger.info(f"[blue]FUNCTION CALL:[/blue] search_lost_and_found(item_type={item_type})")

    # Mock some found items
    if not LOST_AND_FOUND:
        # Add some sample data
        LOST_AND_FOUND.extend([
            {
                "item_id": 101,
                "description": "Black iPhone 15 Pro",
                "location_found": "Floor 3, Food Court",
                "date_found": "2025-12-13",
                "status": "Available at Customer Service"
            },
            {
                "item_id": 102,
                "description": "Brown leather wallet",
                "location_found": "Floor 1, Near Fashion Forward",
                "date_found": "2025-12-12",
                "status": "Available at Customer Service"
            },
            {
                "item_id": 103,
                "description": "Car keys with BMW keychain",
                "location_found": "Parking B2",
                "date_found": "2025-12-14",
                "status": "Available at Customer Service"
            }
        ])

    # Search for matching items
    item_type_lower = item_type.lower()
    matching_items = [
        item for item in LOST_AND_FOUND
        if item_type_lower in item["description"].lower()
    ]

    result = {
        "search_term": item_type,
        "total_found": len(matching_items),
        "matching_items": matching_items,
        "instructions": "If you found your item, please visit Customer Service (Floor 1, Main Entrance) with a valid ID to claim it."
    }

    logger.info(f"[green]Found {len(matching_items)} matching items[/green]")
    return TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        mcp.run(transport="stdio")
