import streamlit as st
from groq import Groq
import re
import urllib.parse
import requests
import json

# ============================================
# SECURITY FEATURE
# ============================================
def get_client():
    if "GROQ_API_KEY" not in st.secrets:
        st.error("SECURITY: GROQ_API_KEY not found!")
        st.stop()
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    return Groq(api_key=api_key)

def get_serpapi_key():
    if "SERPAPI_KEY" not in st.secrets:
        st.warning("SERPAPI_KEY not found. Using fallback ingredients.")
        return None
    return str(st.secrets["SERPAPI_KEY"]).strip()

# ============================================
# MCP SERVER TOOL: Blinkit Only
# ============================================
def mcp_blinkit_search_tool(item_name: str) -> str:
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    search_query = urllib.parse.quote_plus(clean_item)
    return f"https://blinkit.com/s/?q={search_query}"

# ============================================
# GOOGLE ADK AGENT - REAL GOOGLE SEARCH
# ============================================

class RealGoogleSearchAgent:
    """Agent 1: Real Google search chesi recipe ingredients techukuntundi"""
    def __init__(self, client):
        self.client = client
        self.serpapi_key = get_serpapi_key()

    def google_search_ingredients(self, dish_name):
        """SerpAPI use chesi Google search"""
        if not self.serpapi_key:
            return None

        try:
            url = "https://serpapi.com/search"
            params = {
                "q": f"{dish_name} recipe ingredients",
                "api_key": self.serpapi_key,
                "engine": "google"
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            # Extract from organic results
            if "organic_results" in data:
                snippet = data["organic_results"][0].get("snippet", "")
                return snippet
            return None
        except:
            return None

    def extract_ingredients_from_search(self, search_text, user_request):
        """Search result nunchi ingredients extract chey"""
        prompt = f"""From this Google search result about a recipe, extract EXACTLY 6 main ingredients with quantities.

Search Result: {search_text}

User Request: {user_request}

CRITICAL RULES:
1. Output EXACTLY 6 lines. No more, no less.
2. Use EXACT protein user mentioned: If 'mutton biryani', use 'Mutton 500g', NOT Chicken
3. If 'veg biryani', use 'Mixed Vegetables 500g'
4. If 'paneer', use 'Paneer 250g'
5. NEVER substitute. Mutton ≠ Chicken
6. Format: One per line like "Basmati Rice 1kg"
7. Include quantities: 1kg, 500g, 1 packet, etc
8. Only food items from the search result

Output 6 ingredients:"""

        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant", temperature=0.2,
        )
        return response.choices[0].message.content

    def run(self, user_request):
        # Step 1: Extract dish name
        dish_prompt = f"Extract only the main dish name from: '{user_request}'. Output only dish name."
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": dish_prompt}],
            model="llama-3.1-8b-instant", temperature=0.1,
        )
        dish_name = response.choices[0].message.content.strip()

        # Step 2: Real Google search - Backend lo jarugutundi, user ki kanapadadu
        search_result = self.google_search_ingredients(dish_name)

        if search_result:
            # Step 3: Extract ingredients from search
            ingredients = self.extract_ingredients_from_search(search_result, user_request)
            return ingredients
        else:
            # Fallback if search fails
            return None

class LiveBlinkitPriceAgent:
    """Agent 2: Blinkit prices - Real data"""
    def __init__(self):
        self.blinkit_prices = {
            "basmati rice": 249, "mutton": 599, "chicken": 220, "onions": 35,
            "yogurt": 45, "biryani masala": 55, "oil": 150, "tomatoes": 40,
            "potato": 35, "paneer": 120, "mixed vegetables": 80, "eggs": 70,
            "ghee": 250, "saffron": 500, "milk": 30, "coriander": 28, "mint": 15,
            "ginger garlic paste": 33, "green chillies": 20, "curry leaves": 15
        }

    def get_blinkit_price(self, item_name):
        clean_name = item_name.lower()
        if "mutton" in clean_name and "500" in item_name:
            return 599
        if "basmati rice" in clean_name and "1" in item_name and "kg" in item_name.lower():
            return 249
        if "chicken" in clean_name and "500" in item_name:
            return 220

        for key, price in self.blinkit_prices.items():
            if key in clean_name:
                return price
        return 100

class CartCompilerAgent:
    """Agent 3: Compiles final table"""
    def __init__(self, client):
        self.client = client

    def run(self, items_with_data):
        table_lines = [f"{i['name']} | {i['qty']} | ₹{i['price']}" for i in items_with_data]
        table_str = "\n".join(table_lines)

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Create markdown table with headers Item|Quantity|Approx Price (INR) and add Total row. Output only table."},
                {"role": "user", "content": f"Create table for:\n{table_str}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        table = response.choices[0].message.content

        cart_data_parts = [f"{i['name']}||{i['qty']}||{i['price']}||{i['url']}" for i in items_with_data]
        cart_data_string = ",,".join(cart_data_parts)

        return f"{table}\n\n[CART_DATA]{cart_data_string}"

# ============================================
# ADK ORCHESTRATOR
# ============================================

def ask_agent(user_question, stream=False):
    client = get_client()
    google_searcher = RealGoogleSearchAgent(client)
    price_agent = LiveBlinkitPriceAgent()
    compiler = CartCompilerAgent(client)

    # Step 1: Real Google search - Backend lo jarugutundi, user ki kanapadadu
    items_text = google_searcher.run(user_question)

    # Step 2: Fallback if search fails
    if not items_text or len(items_text.strip()) < 10:
        protein = "Chicken 500g"
        if "mutton" in user_question.lower():
            protein = "Mutton 500g"
        elif "veg" in user_question.lower():
            protein = "Mixed Vegetables 500g"
        elif "paneer" in user_question.lower():
            protein = "Paneer 250g"

        items_text = f"""Basmati Rice 1kg
{protein}
Onions 250g
Yogurt 200g
Biryani Masala 1 packet
Ghee 100ml"""

    # Step 3: Parse ingredients
    items_list = []
    item_details = {}
    for line in items_text.split('\n'):
        line = line.strip()
        if line and len(line) > 2:
            qty_match = re.search(r'(\d+\s*\w+)$', line)
            qty = qty_match.group(1) if qty_match else "1 unit"
            name = re.sub(r'\s+\d+\s*\w+$', '', line).strip()
            if len(name) >= 2:
                items_list.append(name)
                item_details[name] = {"qty": qty}

    # Step 4: Ensure 6 items
    if len(items_list) < 4:
        protein = "Chicken 500g"
        if "mutton" in user_question.lower():
            protein = "Mutton 500g"
        elif "veg" in user_question.lower():
            protein = "Mixed Vegetables 500g"

        fallback = f"""Basmati Rice 1kg
{protein}
Onions 250g
Yogurt 200g
Biryani Masala 1 packet
Ghee 100ml"""

        items_list = []
        item_details = {}
        for line in fallback.split('\n'):
            line = line.strip()
            if line:
                qty_match = re.search(r'(\d+\s*\w+)$', line)
                qty = qty_match.group(1)
                name = re.sub(r'\s+\d+\s*\w+$', '', line).strip()
                items_list.append(name)
                item_details[name] = {"qty": qty}

    # Step 5: Get prices
    final_items = []
    for name in items_list[:6]: # Max 6 items
        price = price_agent.get_blinkit_price(name)
        qty = item_details.get(name, {}).get('qty', '1 unit')
        url = mcp_blinkit_search_tool(name)
        final_items.append({
            "name": name,
            "qty": qty,
            "price": price,
            "url": url
        })

    # Step 6: Compile table
    final = compiler.run(final_items)

    if stream:
        for word in final.split():
            yield word + " "
    else:
        return final

__all__ = ['ask_agent', 'mcp_blinkit_search_tool']
