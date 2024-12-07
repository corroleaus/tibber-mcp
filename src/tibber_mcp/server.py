import asyncio
import os
from datetime import datetime, timezone, timedelta
import sys
from typing import Any

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from tibber import Tibber

server = Server("tibber-mcp")

# Initialize Tibber client
ACCESS_TOKEN = os.getenv("TIBBER_TOKEN")
if not ACCESS_TOKEN:
    raise ValueError("TIBBER_TOKEN environment variable required")

# Constants for Tibber client
USER_AGENT = "tibber-mcp/0.1.0"
TIMEOUT = 30  # seconds

tibber_connection = None



@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for interacting with Tibber data."""
    return [
        types.Tool(
            name="list-homes",
            description="List all Tibber homes and their basic information",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get-consumption", 
            description="Get energy consumption data for a specific home",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours of historical data to retrieve",
                        "default": 24
                    }
                },
                "required": ["home_id"]
            }
        ),
        types.Tool(
            name="get-production",
            description="Get energy production data for a specific home",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours of historical data to retrieve",
                        "default": 24
                    }
                },
                "required": ["home_id"]
            }
        ),
        types.Tool(
            name="get-price-info",
            description="Get current and upcoming electricity prices for a specific home",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    }
                },
                "required": ["home_id"]
            }
        ),
        types.Tool(
            name="get-realtime",
            description="Get latest real-time power readings from a home",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    }
                },
                "required": ["home_id"]
            }
        ),
        types.Tool(
            name="get-historic",
            description="Get historical data with custom resolution and optional start date",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Time resolution of data",
                        "enum": ["HOURLY", "DAILY", "WEEKLY", "MONTHLY", "ANNUAL"],
                        "default": "HOURLY"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of data points to retrieve. If start_date is provided and count is 0, will fetch until end of month.",
                        "default": 24
                    },
                    "production": {
                        "type": "boolean",
                        "description": "Get production instead of consumption data",
                        "default": False
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date in YYYY-MM-DD format. If provided, count becomes optional.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    }
                },
                "required": ["home_id"]
            }
        ),
        types.Tool(
            name="get-price-forecast",
            description="Get detailed price forecasts for today and tomorrow",
            inputSchema={
                "type": "object",
                "properties": {
                    "home_id": {
                        "type": "string",
                        "description": "The Tibber home ID"
                    }
                },
                "required": ["home_id"]
            }
        )
    ]

async def get_tibber_connection() -> Tibber:
    """Get or create Tibber connection."""
    global tibber_connection
    if not tibber_connection:
        tibber_connection = Tibber(
            access_token=ACCESS_TOKEN,
            user_agent=USER_AGENT,
            timeout=TIMEOUT
        )
        await tibber_connection.update_info()
    return tibber_connection

async def handle_list_homes() -> list[types.TextContent]:
    """Handle list-homes tool request."""
    try:
        tibber = await get_tibber_connection()
        homes = tibber.get_homes()
        response_text = ["Available Tibber Homes:"]
        
        for home in homes:
            await home.update_info()
            response_text.extend([
                f"\nHome: {home.name}",
                f"ID: {home.home_id}",
                f"Address: {home.address1}",
                f"Country: {home.country}",
                f"Currency: {home.currency}",
                f"Has Active Subscription: {home.has_active_subscription}",
                f"Has Real-time Consumption: {home.has_real_time_consumption}",
                f"Has Production: {home.has_production}",
                f"Metering Point Data:",
                f"  - Grid Company: {home.info.get('viewer', {}).get('home', {}).get('meteringPointData', {}).get('gridCompany', 'N/A')}",
                f"  - Estimated Annual Consumption: {home.info.get('viewer', {}).get('home', {}).get('meteringPointData', {}).get('estimatedAnnualConsumption', 'N/A')} kWh",
                f"  - Energy Tax Type: {home.info.get('viewer', {}).get('home', {}).get('meteringPointData', {}).get('energyTaxType', 'N/A')}",
                f"  - VAT Type: {home.info.get('viewer', {}).get('home', {}).get('meteringPointData', {}).get('vatType', 'N/A')}"
            ])
        
        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error listing homes: {str(e)}"
        )]

async def handle_get_production(home_id: str, hours: int) -> list[types.TextContent]:
    """Handle get-production tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        if not home.has_production:
            return [types.TextContent(
                type="text",
                text=f"This home does not have production capability"
            )]

        production_data = await home.get_historic_data(hours, production=True)
        if not production_data:
            return [types.TextContent(
                type="text",
                text="No production data available for the specified period"
            )]
        
        response_text = ["Energy Production Data:"]
        for entry in production_data:
            timestamp = datetime.fromisoformat(entry["from"]).astimezone(timezone.utc)
            production = entry.get("production", 0)
            profit = entry.get("profit", 0)
            # Format values with None checks
            time_str = timestamp.strftime('%Y-%m-%d %H:%M UTC') if timestamp else 'N/A'
            production_str = f"{production:.2f} kWh" if production is not None else 'N/A'
            profit_str = f"{profit:.2f} {home.currency}" if profit is not None and home.currency else 'N/A'
            
            response_text.append(
                f"\nTime: {time_str}"
                f"\nProduction: {production_str}"
                f"\nProfit: {profit_str}"
            )

        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting production data: {str(e)}"
        )]

async def handle_get_price_info(home_id: str) -> list[types.TextContent]:
    """Handle get-price-info tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        await home.update_price_info()
        current_price, price_level, price_time, price_rank = home.current_price_data()
        daily_prices = home.current_attributes()
        
        response_text = ["Electricity Price Information:"]
        
        if current_price and price_time:
            response_text.extend([
                f"\nCurrent Price ({price_time.strftime('%Y-%m-%d %H:%M')})",
                f"Price: {current_price:.3f} {home.price_unit}",
                f"Level: {price_level or 'N/A'}",
                f"Rank today: {price_rank or 'N/A'}/24"
            ])
        
        response_text.extend([
            f"\nToday's Price Statistics:",
            f"Maximum: {daily_prices['max_price']:.3f} {home.price_unit}",
            f"Average: {daily_prices['avg_price']:.3f} {home.price_unit}",
            f"Minimum: {daily_prices['min_price']:.3f} {home.price_unit}",
            f"\nAverage Prices by Period:",
            f"Night (00-08): {daily_prices['off_peak_1']:.3f} {home.price_unit}",
            f"Day (08-20): {daily_prices['peak']:.3f} {home.price_unit}",
            f"Evening (20-24): {daily_prices['off_peak_2']:.3f} {home.price_unit}"
        ])

        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting price information: {str(e)}"
        )]

async def handle_get_consumption(home_id: str, hours: int) -> list[types.TextContent]:
    """Handle get-consumption tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        await home.update_info()
        await home.fetch_consumption_data()
        consumption_data = await home.get_historic_data(hours)
        if not consumption_data:
            return [types.TextContent(
                type="text",
                text="No consumption data available for the specified period"
            )]
        
        response_text = ["Energy Consumption Data:"]
        for entry in consumption_data:
            timestamp = datetime.fromisoformat(entry["from"]).astimezone(timezone.utc)
            consumption = entry.get("consumption", 0)
            cost = entry.get("cost", 0)
            # Format values with None checks
            time_str = timestamp.strftime('%Y-%m-%d %H:%M UTC') if timestamp else 'N/A'
            consumption_str = f"{consumption:.2f} kWh" if consumption is not None else 'N/A'
            cost_str = f"{cost:.2f} {home.currency}" if cost is not None and home.currency else 'N/A'
            
            response_text.append(
                f"\nTime: {time_str}"
                f"\nConsumption: {consumption_str}"
                f"\nCost: {cost_str}"
            )

        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting consumption data: {str(e)}"
        )]

async def handle_get_realtime(home_id: str) -> list[types.TextContent]:
    """Handle get-realtime tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        if not home.has_real_time_consumption:
            return [types.TextContent(
                type="text",
                text="This home does not have real-time monitoring capability"
            )]

        # Set up a future to store the result
        result_future = asyncio.Future()
        
        def callback(data: dict) -> None:
            """Callback for real-time data."""
            if not result_future.done():
                result_future.set_result(data)

        # Subscribe to real-time updates
        await home.rt_subscribe(callback)
        
        try:
            # Wait for first reading with timeout
            data = await asyncio.wait_for(result_future, timeout=30.0)
            
            if not data or "data" not in data:
                return [types.TextContent(
                    type="text",
                    text="No real-time data received"
                )]
            
            live = data["data"]["liveMeasurement"]
            
            response_text = ["Real-time Power Reading:"]
            response_text.extend([
                f"\nTimestamp: {live.get('timestamp', 'N/A')}",
                f"Power: {live.get('power', 'N/A')} W",
                f"Accumulated Consumption: {live.get('accumulatedConsumption', 'N/A')} kWh",
                f"Accumulated Cost: {live.get('accumulatedCost', 'N/A')} {live.get('currency', '')}",
                "\nPower Details:",
                f"Average Power: {live.get('averagePower', 'N/A')} W",
                f"Min Power: {live.get('minPower', 'N/A')} W",
                f"Max Power: {live.get('maxPower', 'N/A')} W",
                "\nVoltage Readings:",
                f"Phase 1: {live.get('voltagePhase1', 'N/A')} V",
                f"Phase 2: {live.get('voltagePhase2', 'N/A')} V",
                f"Phase 3: {live.get('voltagePhase3', 'N/A')} V",
                "\nCurrent Readings:",
                f"Phase 1: {live.get('currentL1', 'N/A')} A",
                f"Phase 2: {live.get('currentL2', 'N/A')} A",
                f"Phase 3: {live.get('currentL3', 'N/A')} A",
                f"\nPower Factor: {live.get('powerFactor', 'N/A')}",
                f"Signal Strength: {live.get('signalStrength', 'N/A')} %"
            ])
            
            return [types.TextContent(
                type="text",
                text="\n".join(response_text)
            )]
            
        finally:
            # Clean up subscription
            home.rt_unsubscribe()
            
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting real-time data: {str(e)}"
        )]

async def handle_get_price_forecast(home_id: str) -> list[types.TextContent]:
    """Handle get-price-forecast tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        await home.update_price_info()
        price_info = home.price_total
        price_levels = home.price_level
        
        if not price_info:
            return [types.TextContent(
                type="text",
                text="No price forecast data available"
            )]

        response_text = ["Price Forecast:"]
        
        # Sort prices by timestamp
        sorted_times = sorted(price_info.keys())
        current_time = datetime.now(timezone.utc)
        
        # Group prices by day
        today_prices = []
        tomorrow_prices = []
        
        for time_str in sorted_times:
            price_time = datetime.fromisoformat(time_str)
            if price_time.date() == current_time.date():
                today_prices.append((time_str, price_info[time_str], price_levels.get(time_str, "UNKNOWN")))
            elif price_time.date() == current_time.date() + timedelta(days=1):
                tomorrow_prices.append((time_str, price_info[time_str], price_levels.get(time_str, "UNKNOWN")))

        # Format today's prices
        if today_prices:
            response_text.append("\nToday's Prices:")
            for time_str, price, level in today_prices:
                time = datetime.fromisoformat(time_str)
                response_text.append(
                    f"\n{time.strftime('%H:%M')}: {price:.3f} {home.price_unit}"
                    f" ({level})"
                )

        # Format tomorrow's prices
        if tomorrow_prices:
            response_text.append("\nTomorrow's Prices:")
            for time_str, price, level in tomorrow_prices:
                time = datetime.fromisoformat(time_str)
                response_text.append(
                    f"\n{time.strftime('%H:%M')}: {price:.3f} {home.price_unit}"
                    f" ({level})"
                )

        # Add price statistics
        daily_stats = home.current_attributes()
        response_text.extend([
            "\nPrice Statistics:",
            f"Maximum: {daily_stats['max_price']:.3f} {home.price_unit}",
            f"Average: {daily_stats['avg_price']:.3f} {home.price_unit}",
            f"Minimum: {daily_stats['min_price']:.3f} {home.price_unit}",
            "\nAverage Prices by Period:",
            f"Night (00-08): {daily_stats['off_peak_1']:.3f} {home.price_unit}",
            f"Day (08-20): {daily_stats['peak']:.3f} {home.price_unit}",
            f"Evening (20-24): {daily_stats['off_peak_2']:.3f} {home.price_unit}"
        ])

        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting price forecast: {str(e)}"
        )]

async def handle_get_historic(
    home_id: str, 
    resolution: str = "HOURLY", 
    count: int = 24, 
    production: bool = False,
    start_date: str | None = None
) -> list[types.TextContent]:
    """Handle get-historic tool request.
    
    Args:
        home_id: The Tibber home ID
        resolution: Time resolution (HOURLY, DAILY, WEEKLY, MONTHLY, ANNUAL)
        count: Number of data points to retrieve
        production: Whether to get production instead of consumption data
        start_date: Optional start date in YYYY-MM-DD format
    """
    """Handle get-historic tool request."""
    try:
        tibber = await get_tibber_connection()
        home = tibber.get_home(home_id)
        if not home:
            return [types.TextContent(
                type="text",
                text=f"No home found with ID {home_id}"
            )]

        if production and not home.has_production:
            return [types.TextContent(
                type="text",
                text="This home does not have production capability"
            )]
        if start_date:
            try:
                date_from = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                print(date_from, file=sys.stderr)
                historic_data = await home.get_historic_data_date(
                    date_from=date_from,
                    n_data=count,
                    resolution=resolution,
                    production=production
                )
            except ValueError:
                return [types.TextContent(
                    type="text",
                    text=f"Invalid date format: {start_date}. Please use YYYY-MM-DD format."
                )]
        else:
            if start_date:
                try:
                    date_from = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    historic_data = await home.get_historic_data_date(
                        date_from=date_from,
                        n_data=count,
                        resolution=resolution,
                        production=production
                    )
                except ValueError:
                    return [types.TextContent(
                        type="text",
                        text=f"Invalid date format: {start_date}. Please use YYYY-MM-DD format."
                    )]
            else:
                historic_data = await home.get_historic_data(
                    count,
                    resolution=resolution,
                    production=production
                )
        if not historic_data:
            return [types.TextContent(
                type="text",
                text=f"No {'production' if production else 'consumption'} data available for the specified period"
            )]
        
        data_type = "Production" if production else "Consumption"
        response_text = [f"Historical {data_type} Data ({resolution}):"]
        
        for entry in historic_data:
            timestamp = datetime.fromisoformat(entry["from"]).astimezone(timezone.utc)
            value = entry.get("production" if production else "consumption", 0)
            cost = entry.get("profit" if production else "cost", 0)
            
            # Format values with None checks
            time_str = timestamp.strftime('%Y-%m-%d %H:%M UTC') if timestamp else 'N/A'
            value_str = f"{value:.2f} kWh" if value is not None else 'N/A'
            cost_str = f"{cost:.2f} {home.currency}" if cost is not None and home.currency else 'N/A'
            
            response_text.append(
                f"\nTime: {time_str}"
                f"\n{data_type}: {value_str}"
                f"\n{'Profit' if production else 'Cost'}: {cost_str}"
            )

        return [types.TextContent(
            type="text",
            text="\n".join(response_text)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error getting historic data: {str(e)}"
        )]
        
@server.call_tool() 
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    global tibber_connection
    
    if not arguments and name != "list-homes":
        raise ValueError("Missing arguments")

    if name == "list-homes":
        return await handle_list_homes()
    
    elif name == "get-production":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        hours = int(arguments.get("hours", 24))
        return await handle_get_production(home_id, hours)
    
    elif name == "get-price-info":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        return await handle_get_price_info(home_id)
    
    elif name == "get-consumption":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        hours = int(arguments.get("hours", 24))
        return await handle_get_consumption(home_id, hours)
    
    elif name == "get-realtime":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        return await handle_get_realtime(home_id)
    
    elif name == "get-historic":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        resolution = arguments.get("resolution", "HOURLY")
        count = int(arguments.get("count", 24))
        production = bool(arguments.get("production", False))
        start_date = arguments.get("start_date")
        return await handle_get_historic(home_id, resolution, count, production, start_date)
    
    elif name == "get-price-forecast":
        home_id = arguments.get("home_id")
        if not home_id:
            raise ValueError("Missing home_id")
        return await handle_get_price_forecast(home_id)
    
    else:
        raise ValueError(f"Unknown tool: {name}")

async def cleanup():
    """Cleanup Tibber connection."""
    global tibber_connection
    if tibber_connection:
        await tibber_connection.close_connection()
        tibber_connection = None



async def main():
    # Run the server using stdin/stdout streams
    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tibber-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    finally:
        await cleanup()
