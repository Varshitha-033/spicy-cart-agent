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
3. For food requests, you MUST extract 4-6 SPECIFIC ingredient names with quantities. NEVER give less than 4.
4. CRITICAL: Use EXACT protein/variant user mentioned. If user says 'mutton biryani', MUST include 'Mutton 500g', NOT Chicken.
5. If user says 'veg biryani', use 'Mixed Vegetables 500g'. If 'chicken biryani', use 'Chicken 500g'. If 'paneer', use 'Paneer 250g'.
6. NEVER substitute user's request. Mutton ≠ Chicken. Respect user choice.
7. NEVER use generic words like 'item', 'ingredient', 'product'
8. Output format: One ingredient per line. Example: Basmati Rice 1kg
9. QUANTITY MANDATORY: Every line must have number + unit like 1kg, 500g, 1 packet"""

    def run(self, user_request):
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": f"Extract 4-6 food ingredients from: {user_request}. Must give at least 4 items. Use exact protein type mentioned by user."}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
        )
        return response.choices[0].message.content

class PriceEstimatorAgent:
    """Agent 2: Estimates prices for Indian grocery items"""
    def __init__(self, client):
        self.client = client
        self.role = """You are PriceEstimatorAgent. Give realistic INR prices for Indian grocery items only.
Format each line as: Item Name | Quantity | Price
Use current Indian Blinkit rates. Be specific with ingredient names. Mutton is costlier than Chicken."""

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
            if '|' in line and 'Total' not in line and 'Item' not in line:
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

        # Use || as delimiter to avoid URL splitting
        cart_data_parts = [f"{i['name']}||{i['qty']}||{i['price']}||{i['url']}" for i in items_with_urls]
        cart_data_string = ",,".join(cart_data_parts)

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

    # Safety check - minimum 3 items ensure chey
    items_list = [i.strip() for i in items.split('\n') if i.strip() and len(i.strip()) > 2]

    if len(items_list) < 3:
        # FIX: User request lo unna protein vadali
        protein = "Chicken 500g" # default
        if "mutton" in user_question.lower():
            protein = "Mutton 500g"
        elif "veg" in user_question.lower() or "vegetable" in user_question.lower():
            protein = "Mixed Vegetables 500g"
        elif "paneer" in user_question.lower():
            protein = "Paneer 250g"
        elif "egg" in user_question.lower():
            protein = "Eggs 6 pieces"
        elif "fish" in user_question.lower():
            protein = "Fish 500g"

        if "biryani" in user_question.lower():
            items = f"Basmati Rice 1kg\n{protein}\nOnions 250g\nYogurt 200g\nBiryani Masala 1 packet\nOil 100ml"
        elif "dosa" in user_question.lower():
            items = "Dosa Batter 1kg\nOil 200ml\nPotato 500g\nOnions 250g\nCurry Leaves 1 bunch\nMustard Seeds 50g"
        else:
            items = f"Rice 1kg\n{protein}\nOil 1L\nOnions 1kg\nTomatoes 500g\nSpices 1 packet"

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
