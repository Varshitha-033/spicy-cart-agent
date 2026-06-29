import streamlit as st
from groq import Groq
import re
import urllib.parse

# ============================================
# SECURITY FEATURE
# ============================================
def get_client():
    if "GROQ_API_KEY" not in st.secrets:
        st.error("SECURITY: GROQ_API_KEY not found! Add in Streamlit Cloud -> Settings -> Secrets")
        st.stop()
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    if len(api_key)!= 56:
        st.error(f"SECURITY: Invalid GROQ_API_KEY length. Expected 56, got {len(api_key)}")
        st.stop()
    return Groq(api_key=api_key)

# ============================================
# MCP SERVER TOOL: Blinkit Only
# ============================================
def mcp_blinkit_search_tool(item_name: str) -> str:
    """MCP Tool: search_blinkit - Food items only"""
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    if not clean_item:
        return "https://blinkit.com"
    search_query = urllib.parse.quote_plus(clean_item)
    return f"https://blinkit.com/s/?q={search_query}"

# ============================================
# GOOGLE ADK MULTI-AGENT SYSTEM - FOOD ONLY
# ============================================

class FoodParserAgent:
    """Agent 1: Extracts ONLY food ingredients. Rejects non-food."""
    def __init__(self, client):
        self.client = client
        self.role = """You are FoodParserAgent. CRITICAL RULES:
1. ONLY accept food/recipe/cooking related requests
2. If user asks for clothes, electronics, or non-food items, output exactly: NOT_FOOD_REQUEST
3. For food requests, extract 3-6 SPECIFIC ingredient names with quantities
4. NEVER use generic words like 'item', 'ingredient', 'product'
5. Output format: One ingredient per line. Example: Basmati Rice 1kg
6. If request is vague like 'biryani', list common ingredients"""

    def run(self, user_request):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Extract food ingredients from: {user_request}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        return response.choices[0].message.content

class PriceEstimatorAgent:
    """Agent 2: Estimates prices for Indian grocery items"""
    def __init__(self, client):
        self.client = client
        self.role = """You are PriceEstimatorAgent. Give realistic INR prices for Indian grocery items only.
Format each line as: Item Name | Quantity | Price
Use current Indian Blinkit rates. Be specific with ingredient names."""

    def run(self, items_list):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Add realistic Blinkit INR prices for these ingredients:\n{items_list}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.5,
        )
        return response.choices[0].message.content

class CartCompilerAgent:
    """Agent 3: Compiles final table with Blinkit links"""
    def __init__(self, client):
        self.client = client

    def run(self, priced_items):
        # Parse items and add Blinkit URLs
        items_with_urls = []
        for line in priced_items.split('\n'):
            if '|' in line and 'Total' not in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    name = parts[0].strip()
                    qty = parts[1].strip()
                    price = parts[2].strip().replace('₹','')
                    url = mcp_blinkit_search_tool(name)
                    items_with_urls.append({
                        "name": name, "qty": qty, "price": price, "url": url
                    })

        # Create table via LLM
        table_lines = [f"{i['name']} | {i['qty']} | ₹{i['price']}" for i in items_with_urls]
        table_str = "\n".join(table_lines)

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Create markdown table with headers Item|Quantity|Approx Price (INR) and add Total row. Output only table."},
                {"role": "user", "content": f"Create table for:\n{table_str}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        table = response.choices[0].message.content

        # FIX: Use || as delimiter instead of : to avoid URL splitting
        cart_data_parts = [f"{i['name']}||{i['qty']}||{i['price']}||{i['url']}" for i in items_with_urls]
        cart_data_string = ",,".join(cart_data_parts) # Use,, to separate items

        return f"{table}\n\n[CART_DATA]{cart_data_string}"

# ============================================
# ADK ORCHESTRATOR
# ============================================

def ask_agent(user_question, stream=False):
    client = get_client()
    parser = FoodParserAgent(client)
    pricer = PriceEstimatorAgent(client)
    compiler = CartCompilerAgent(client)

    # Step 1: Check if food request
    items = parser.run(user_question)

    if "NOT_FOOD_REQUEST" in items:
        return "Sorry, I only help with food recipes and grocery ingredients. Try: 'Chicken biryani for 4' or 'Monthly vegetables list'"

    # Step 2: Price estimation
    priced = pricer.run(items)

    # Step 3: Compile with Blinkit links
    final = compiler.run(priced)

    if stream:
        for word in final.split():
            yield word + " "
    else:
        return final

__all__ = ['ask_agent', 'mcp_blinkit_search_tool']
