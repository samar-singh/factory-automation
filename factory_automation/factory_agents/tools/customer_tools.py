"""Customer management and context tools"""

import json
import logging

from agents import function_tool

logger = logging.getLogger(__name__)


class CustomerTools:
    """Customer context and management tools"""
    
    def __init__(self, chromadb_client, mode="execute"):
        """
        Initialize customer tools
        
        Args:
            chromadb_client: ChromaDB client for customer data
            mode: "execute" for v3, "propose" for v4
        """
        self.chromadb_client = chromadb_client
        self.mode = mode
    
    def create_tools(self):
        """Create and return customer-related tools"""
        tools = []
        
        # Customer context tool
        @function_tool(
            name_override="get_customer_context",
            description_override="Retrieve customer history and preferences. Use AFTER email classification to understand customer background. Do NOT use before knowing who the customer is.",
        )
        async def get_customer_context(customer_email: str) -> str:
            """Get historical context and preferences for a customer.
            
            This tool retrieves customer information including order history, preferences,
            and payment patterns. Use this AFTER email classification to understand the
            customer's background and provide personalized service.
            
            Args:
                customer_email: Customer's email address to look up (e.g., "customer@company.com")
            
            Returns:
                String summary (execute mode) or JSON object (propose mode) with:
                - Customer tier (new, returning, regular, premium)
                - Order count and history
                - Product preferences
                - Payment history quality
                - Recommended actions based on customer profile
            """
            try:
                # Mock known customers for demo
                known_customers = {
                    "allen.solly@example.com": {
                        "tier": "regular",
                        "orders": 15,
                        "preferences": "black woven tags",
                        "payment_history": "excellent"
                    },
                    "myntra@example.com": {
                        "tier": "premium",
                        "orders": 25,
                        "preferences": "eco-friendly materials",
                        "payment_history": "excellent"
                    },
                    "ops@zara.com": {
                        "tier": "new",
                        "orders": 2,
                        "preferences": "leather tags",
                        "payment_history": "good"
                    },
                }
                
                if customer_email in known_customers:
                    customer_data = known_customers[customer_email]
                    if self.mode == "execute":
                        return f"{customer_data['tier'].title()} customer: {customer_data['orders']} orders, prefers {customer_data['preferences']}"
                    else:
                        return json.dumps({
                            "customer_email": customer_email,
                            "tier": customer_data["tier"],
                            "order_count": customer_data["orders"],
                            "preferences": customer_data["preferences"],
                            "payment_history": customer_data["payment_history"],
                            "recommendations": [
                                f"Offer {customer_data['preferences']}",
                                f"Apply {customer_data['tier']} pricing",
                                "Prioritize based on history"
                            ]
                        })
                
                # Search for previous orders in ChromaDB
                results = self.chromadb_client.collection.query(
                    query_texts=[f"orders from {customer_email}"],
                    n_results=10,
                    where=(
                        {"customer_email": customer_email}
                        if hasattr(self.chromadb_client, "customer_field")
                        else None
                    ),
                    include=["metadatas"],
                )
                
                order_count = 0
                if results and results.get("metadatas") and results["metadatas"][0]:
                    order_count = len(results["metadatas"][0])
                
                if self.mode == "execute":
                    if order_count > 5:
                        return f"Regular customer: {order_count} previous orders"
                    elif order_count > 0:
                        return f"Returning customer: {order_count} previous orders"
                    else:
                        return "New customer: No order history"
                else:
                    tier = "regular" if order_count > 5 else "returning" if order_count > 0 else "new"
                    return json.dumps({
                        "customer_email": customer_email,
                        "tier": tier,
                        "order_count": order_count,
                        "preferences": "unknown",
                        "payment_history": "unknown",
                        "recommendations": [
                            "Verify customer details",
                            "Apply standard pricing",
                            "Monitor order closely" if tier == "new" else "Process normally"
                        ]
                    })
                
            except Exception as e:
                logger.error(f"Error getting customer context: {e}")
                if self.mode == "execute":
                    return "Customer history unavailable"
                else:
                    return json.dumps({
                        "error": str(e),
                        "customer_email": customer_email,
                        "tier": "unknown"
                    })
        
        tools.append(get_customer_context)
        
        return tools