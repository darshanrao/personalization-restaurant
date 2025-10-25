import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

@dataclass
class OrderItem:
    name: str
    quantity: int
    price: float
    category: str

@dataclass
class Order:
    id: str
    user_id: str
    date: str
    day_of_week: str
    items: List[OrderItem]
    total: float
    restaurant: str

class OrderDatabase:
    """Local JSON database for food orders."""
    
    def __init__(self, db_path: str = "orders.json"):
        self.db_path = db_path
        self.orders: List[Dict[str, Any]] = []
        self.load_orders()
    
    def load_orders(self) -> None:
        """Load orders from JSON file."""
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.orders = data.get('orders', [])
            else:
                self.orders = []
        except Exception as e:
            print(f"Error loading orders: {e}")
            self.orders = []
    
    def save_orders(self) -> None:
        """Save orders to JSON file."""
        try:
            data = {"orders": self.orders}
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving orders: {e}")
    
    def get_orders_by_date(self, date: str, user_id: str = "user_darshan") -> List[Dict[str, Any]]:
        """Get orders for a specific date."""
        return [order for order in self.orders 
                if order['date'] == date and order['user_id'] == user_id]
    
    def get_orders_by_day_of_week(self, day_of_week: str, user_id: str = "user_darshan") -> List[Dict[str, Any]]:
        """Get orders for a specific day of the week."""
        return [order for order in self.orders 
                if order['day_of_week'] == day_of_week and order['user_id'] == user_id]
    
    def get_orders_by_date_range(self, start_date: str, end_date: str, user_id: str = "user_darshan") -> List[Dict[str, Any]]:
        """Get orders within a date range."""
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        result = []
        for order in self.orders:
            if order['user_id'] == user_id:
                order_date = datetime.strptime(order['date'], "%Y-%m-%d")
                if start_dt <= order_date <= end_dt:
                    result.append(order)
        
        return result
    
    def get_latest_order(self, user_id: str = "user_darshan") -> Optional[Dict[str, Any]]:
        """Get the most recent order."""
        user_orders = [order for order in self.orders if order['user_id'] == user_id]
        if not user_orders:
            return None
        
        # Sort by date (most recent first)
        user_orders.sort(key=lambda x: x['date'], reverse=True)
        return user_orders[0]
    
    def get_orders_by_item_name(self, item_name: str, user_id: str = "user_darshan") -> List[Dict[str, Any]]:
        """Get orders containing a specific item."""
        result = []
        for order in self.orders:
            if order['user_id'] == user_id:
                for item in order['items']:
                    if item_name.lower() in item['name'].lower():
                        result.append(order)
                        break
        return result
    
    def add_order(self, order: Dict[str, Any]) -> None:
        """Add a new order to the database."""
        self.orders.append(order)
        self.save_orders()

class OrderSearchTool:
    """Tool for searching food orders that can be called by the LLM."""
    
    def __init__(self):
        self.db = OrderDatabase()
    
    def search_orders(self, query: str, user_id: str = "user_darshan") -> Dict[str, Any]:
        """
        Search orders based on natural language query.
        
        Args:
            query: Natural language query like "last Friday", "pizza orders", "last week"
            user_id: User ID to search for
            
        Returns:
            Dictionary with search results and formatted response
        """
        query_lower = query.lower()
        
        # Parse different types of queries
        if "last friday" in query_lower or "friday" in query_lower:
            return self._search_by_day("Friday", user_id)
        elif "last monday" in query_lower or "monday" in query_lower:
            return self._search_by_day("Monday", user_id)
        elif "last week" in query_lower or "week" in query_lower:
            return self._search_last_week(user_id)
        elif "latest" in query_lower or "most recent" in query_lower:
            return self._search_latest(user_id)
        elif any(food in query_lower for food in ["pizza", "burger", "pasta", "salad", "wings", "fish"]):
            return self._search_by_food_item(query_lower, user_id)
        else:
            return self._search_general(query_lower, user_id)
    
    def _search_by_day(self, day: str, user_id: str) -> Dict[str, Any]:
        """Search orders by day of week."""
        orders = self.db.get_orders_by_day_of_week(day, user_id)
        
        if not orders:
            return {
                "found": False,
                "message": f"No orders found for {day}",
                "orders": []
            }
        
        # Get the most recent order for that day
        latest_order = max(orders, key=lambda x: x['date'])
        
        return {
            "found": True,
            "message": f"Found your {day} order from {latest_order['date']}",
            "orders": [latest_order],
            "formatted_response": self._format_order_response(latest_order)
        }
    
    def _search_last_week(self, user_id: str) -> Dict[str, Any]:
        """Search orders from last week."""
        today = datetime.now()
        last_week_start = today - timedelta(days=today.weekday() + 7)
        last_week_end = last_week_start + timedelta(days=6)
        
        orders = self.db.get_orders_by_date_range(
            last_week_start.strftime("%Y-%m-%d"),
            last_week_end.strftime("%Y-%m-%d"),
            user_id
        )
        
        if not orders:
            return {
                "found": False,
                "message": "No orders found from last week",
                "orders": []
            }
        
        return {
            "found": True,
            "message": f"Found {len(orders)} orders from last week",
            "orders": orders,
            "formatted_response": self._format_multiple_orders_response(orders)
        }
    
    def _search_latest(self, user_id: str) -> Dict[str, Any]:
        """Search for the most recent order."""
        latest_order = self.db.get_latest_order(user_id)
        
        if not latest_order:
            return {
                "found": False,
                "message": "No orders found",
                "orders": []
            }
        
        return {
            "found": True,
            "message": f"Found your latest order from {latest_order['date']}",
            "orders": [latest_order],
            "formatted_response": self._format_order_response(latest_order)
        }
    
    def _search_by_food_item(self, query: str, user_id: str) -> Dict[str, Any]:
        """Search orders by food item."""
        food_keywords = ["pizza", "burger", "pasta", "salad", "wings", "fish", "chicken", "nachos"]
        
        for keyword in food_keywords:
            if keyword in query:
                orders = self.db.get_orders_by_item_name(keyword, user_id)
                
                if orders:
                    return {
                        "found": True,
                        "message": f"Found {len(orders)} orders containing {keyword}",
                        "orders": orders,
                        "formatted_response": self._format_multiple_orders_response(orders)
                    }
        
        return {
            "found": False,
            "message": "No orders found for that food item",
            "orders": []
        }
    
    def _search_general(self, query: str, user_id: str) -> Dict[str, Any]:
        """General search - return latest order as fallback."""
        return self._search_latest(user_id)
    
    def _format_order_response(self, order: Dict[str, Any]) -> str:
        """Format a single order for display."""
        items_text = ", ".join([f"{item['quantity']}x {item['name']}" for item in order['items']])
        return f"On {order['date']} ({order['day_of_week']}), you ordered: {items_text}. Total: ${order['total']:.2f}"
    
    def _format_multiple_orders_response(self, orders: List[Dict[str, Any]]) -> str:
        """Format multiple orders for display."""
        if len(orders) == 1:
            return self._format_order_response(orders[0])
        
        response = f"Found {len(orders)} orders:\n"
        for order in orders[-3:]:  # Show last 3 orders
            items_text = ", ".join([f"{item['quantity']}x {item['name']}" for item in order['items']])
            response += f"• {order['date']} ({order['day_of_week']}): {items_text} - ${order['total']:.2f}\n"
        
        return response.strip()

# Create a global instance
order_search_tool = OrderSearchTool()

class IntelligentOrderSearch:
    """Intelligent order search using LLM to generate queries."""
    
    def __init__(self):
        self.db = OrderDatabase()
        self.query_llm = None
        
        # Initialize query generation LLM
        api_key = os.getenv("NIM_API_KEY")
        api_base = os.getenv("NIM_API_BASE")
        model_name = os.getenv("MODEL_NAME")
        
        if api_key and api_base and model_name:
            try:
                # Use the same NVIDIA Nemotron model as the main LLM
                self.query_llm = ChatOpenAI(
                    model=model_name,
                    base_url=api_base,
                    api_key=api_key,
                    temperature=0.1  # Low temperature for consistent query generation
                )
                print(f"Successfully initialized query generation LLM with NVIDIA Nemotron: {model_name}")
            except Exception as e:
                print(f"Failed to initialize query LLM: {e}")
                self.query_llm = None
    
    def generate_search_query(self, user_query: str, user_id: str = "user_darshan") -> Dict[str, Any]:
        """Use LLM to generate a structured search query from natural language."""
        
        if not self.query_llm:
            raise Exception("Query LLM not initialized. Cannot generate search query.")
        
        prompt = f"""
You are a query generator for a food order database. Convert the user's natural language query into a structured search query.

Available search parameters:
- user_id: "{user_id}" (always include this)
- date: specific date in YYYY-MM-DD format
- day_of_week: "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
- food_item: name of food item (e.g., "pizza", "burger", "wings")
- time_period: "latest", "last_week", "last_month"
- limit: number of results to return (default: 1)

User query: "{user_query}"

Respond with ONLY a JSON object containing the search parameters. Examples:

For "last Friday": {{"user_id": "{user_id}", "day_of_week": "Friday", "limit": 1}}
For "latest order": {{"user_id": "{user_id}", "time_period": "latest", "limit": 1}}
For "pizza orders": {{"user_id": "{user_id}", "food_item": "pizza", "limit": 5}}
For "orders from last week": {{"user_id": "{user_id}", "time_period": "last_week", "limit": 10}}

JSON response:"""

        try:
            response = self.query_llm.invoke(prompt)
            query_params = json.loads(response.content.strip())
            return query_params
        except Exception as e:
            print(f"Error generating query: {e}")
            raise Exception(f"Failed to generate search query: {e}")
    
    
    def execute_search(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the search query against the database."""
        user_id = query_params.get("user_id", "user_darshan")
        limit = query_params.get("limit", 1)
        
        results = []
        
        # Search by day of week
        if "day_of_week" in query_params:
            orders = self.db.get_orders_by_day_of_week(query_params["day_of_week"], user_id)
            results.extend(orders)
        
        # Search by food item
        elif "food_item" in query_params:
            orders = self.db.get_orders_by_item_name(query_params["food_item"], user_id)
            results.extend(orders)
        
        # Search by time period
        elif "time_period" in query_params:
            time_period = query_params["time_period"]
            if time_period == "latest":
                latest_order = self.db.get_latest_order(user_id)
                if latest_order:
                    results.append(latest_order)
            elif time_period == "last_week":
                today = datetime.now()
                last_week_start = today - timedelta(days=today.weekday() + 7)
                last_week_end = last_week_start + timedelta(days=6)
                orders = self.db.get_orders_by_date_range(
                    last_week_start.strftime("%Y-%m-%d"),
                    last_week_end.strftime("%Y-%m-%d"),
                    user_id
                )
                results.extend(orders)
        
        # Search by specific date
        elif "date" in query_params:
            orders = self.db.get_orders_by_date(query_params["date"], user_id)
            results.extend(orders)
        
        # Default: get latest order
        else:
            latest_order = self.db.get_latest_order(user_id)
            if latest_order:
                results.append(latest_order)
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_results = []
        for order in results:
            if order['id'] not in seen_ids:
                seen_ids.add(order['id'])
                unique_results.append(order)
                if len(unique_results) >= limit:
                    break
        
        return unique_results
    
    def search_orders(self, user_query: str, user_id: str = "user_darshan") -> str:
        """Main search function that combines query generation and execution."""
        # Generate search query using LLM
        query_params = self.generate_search_query(user_query, user_id)
        
        # Execute the search
        results = self.execute_search(query_params)
        
        # Format results
        if not results:
            return "No orders found matching your criteria."
        
        if len(results) == 1:
            return self._format_order_response(results[0])
        else:
            return self._format_multiple_orders_response(results)
    
    def _format_order_response(self, order: Dict[str, Any]) -> str:
        """Format a single order for display."""
        items_text = ", ".join([f"{item['quantity']}x {item['name']}" for item in order['items']])
        return f"On {order['date']} ({order['day_of_week']}), you ordered: {items_text}. Total: ${order['total']:.2f}"
    
    def _format_multiple_orders_response(self, orders: List[Dict[str, Any]]) -> str:
        """Format multiple orders for display."""
        if len(orders) == 1:
            return self._format_order_response(orders[0])
        
        response = f"Found {len(orders)} orders:\n"
        for order in orders[-3:]:  # Show last 3 orders
            items_text = ", ".join([f"{item['quantity']}x {item['name']}" for item in order['items']])
            response += f"• {order['date']} ({order['day_of_week']}): {items_text} - ${order['total']:.2f}\n"
        
        return response.strip()

# Create global instance
intelligent_search = IntelligentOrderSearch()

# Single LangChain Tool
@tool
def search_order_history(query: str, user_id: str = "user_darshan") -> str:
    """
    Search for food orders using natural language queries.
    
    This tool can understand queries like:
    - "last Friday" - finds orders from the most recent Friday
    - "latest order" - finds the most recent order
    - "pizza orders" - finds all orders containing pizza
    - "orders from last week" - finds orders from the previous week
    - "burger I had before" - finds orders containing burgers
    
    Args:
        query: Natural language query describing what orders to find
        user_id: User ID to search for (defaults to "user_darshan")
    
    Returns:
        Formatted string with order information or "No orders found" message
    """
    return intelligent_search.search_orders(query, user_id)

# List of available tools (just one!)
ORDER_TOOLS = [search_order_history]
