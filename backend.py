import streamlit as st
from groq import Groq
import re
import urllib.parse
import requests

# ============================================
# SECURITY FEATURE
# ============================================
def get_client():
    if "GROQ_API_KEY" not in st.secrets:
        st.error("GROQ_API_KEY secret not found!")
        st.stop()
    
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    
    if len(api_key)!= 56:
        st.error(f"Invalid key length! Expected 56, got {len(api_key)}.")
        st.stop()
    
    return Groq(api_key=api_key)

def get_serpapi_key():
    if "SERPAPI_KEY" not in st.secrets:
        return None
    return str(st.secrets["SERPAPI_KEY"]).strip()

def get_working_model():
    client = get_client()
    try:
        models = client.models.list().data
        preferred = [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192", 
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant"
        ]
        available_ids = [m.id for m in models]
        for model in preferred:
            if model in available_ids:
                return model
        return available_ids[0]
    except Exception:
        return "llama-3.1-8b-instant"

# ============================================
# MCP SERVER TOOL: Blinkit Only
# ============================================
def mcp_blinkit_search_tool(item_name: str) -> str:
    clean_item = re.sub(r'[^\w\s-]', '', item_name).strip()
    if not clean_item:
        return "https://blinkit.com"
    search_query = urllib.parse.quote_plus(clean_item)
    return f"https://blinkit.com/s/?q={search_query}"

# ============================================
# AGENT 0: Food Request Checker
# ============================================
def is_food_request(user_question, client):
    cleaned = user_question.lower().strip()
    greetings = ['hi', 'hello', 'hey', 'hii', 'helo', 'hola', 'namaste', 'vanakkam', 'thanks', 'ok', 'bye']
    
    if cleaned in greetings or len(cleaned) < 3:
        return False, "GREETING"
    
    check_prompt = f"""Is this asking for food recipe, grocery list, cooking ingredients, or meal planning?
User: "{user_question}"
Answer ONLY: YES or NO"""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": check_prompt}],
        model="llama-3.1-8b-instant", temperature=0.1,
    )
    result = response.choices[0].message.content.strip().upper()
    return "YES" in result, "FOOD" if "YES" in result else "NOT_FOOD"

# ============================================
# AGENT 1: Universal Google Search
# ============================================
def google_search_any_recipe(user_request, client):
    serpapi_key = get_serpapi_key()
    
    dish_prompt = f"""Extract the main dish or recipe name from user request. 
If user asks for 'weekly vegetables', output 'vegetables'.
If user asks for 'paneer curry', output 'paneer curry'.
User: '{user_request}'
Output only dish name:"""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": dish_prompt}],
        model="llama-3.1-8b-instant", temperature=0.1,
    )
    dish_name = response.choices[0].message.content.strip()
    
    search_snippet = None
    if serpapi_key:
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": f"{dish_name} recipe ingredients list quantity",
                "api_key": serpapi_key,
                "engine": "google"
            }
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if "organic_results" in data and len(data["organic_results"]) > 0:
                snippets = []
                for i in range(min(2, len(data["organic_results"]))):
                    snippets.append(data["organic_results"][i].get("snippet", ""))
                search_snippet = " ".join(snippets)
        except:
            pass
    
    if search_snippet:
        extract_prompt = f"""From this Google search result, extract EXACTLY 4-6 main ingredients with quantities.

Search: {search_snippet}
User Request: {user_request}
Dish: {dish_name}

RULES:
1. Output EXACTLY 4-6 lines
2. Use EXACT ingredients from search result or user request
3. If 'mutton' in request, use 'Mutton', NOT 'Chicken'
4. If 'veg', use vegetables, NOT meat
5. Format: "Ingredient Name 500g" or "Ingredient Name 1kg" per line
6. Include realistic quantities: 250g, 500g, 1kg, 1 packet, 2 pieces
7. Only main cooking ingredients

Output 4-6 ingredients:"""
    else:
        extract_prompt = f"""For the recipe "{dish_name}", list EXACTLY 4-6 main ingredients with quantities.
User Request: {user_request}

RULES:
1. Output EXACTLY 4-6 lines
2. Use EXACT protein/item user mentioned
3. If 'mutton' in request, use 'Mutton 500g', NOT Chicken
4. If 'veg', use vegetables
5. Format: "Ingredient Name 500g" per line
6. Realistic Indian cooking quantities

Output 4-6 ingredients:"""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": extract_prompt}],
        model=get_working_model(), temperature=0.3,
    )
    return response.choices[0].message.content

# ============================================
# AGENT 2: Blinkit Price - REALISTIC RATES
# ============================================
def parse_quantity(qty_str):
    qty_str = qty_str.lower()
    match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l|packet|piece|pieces|bunch)', qty_str)
    if match:
        value = float(match.group(1))
        unit = match.group(2)
        return value, unit
    return 1, "unit"

def get_blinkit_price(item_name, qty_str="1 unit"):
    base_prices = {
        "basmati rice": {"1kg": 180, "500g": 95, "unit": "kg"},
        "rice": {"1kg": 60, "500g": 35, "unit": "kg"},
        "wheat flour": {"1kg": 45, "500g": 25, "unit": "kg"},
        "atta": {"1kg": 45, "500g": 25, "unit": "kg"},
        "mutton": {"1kg": 850, "500g": 450, "250g": 230, "unit": "kg"},
        "chicken": {"1kg": 220, "500g": 120, "250g": 65, "unit": "kg"},
        "fish": {"1kg": 350, "500g": 180, "unit": "kg"},
        "prawns": {"1kg": 600, "500g": 320, "unit": "kg"},
        "eggs": {"12": 70, "6": 38, "unit": "pieces"},
        "paneer": {"1kg": 450, "500g": 230, "250g": 120, "200g": 95, "unit": "kg"},
        "tofu": {"200g": 80, "unit": "kg"},
        "onions": {"1kg": 35, "500g": 20, "250g": 12, "unit": "kg"},
        "tomatoes": {"1kg": 40, "500g": 22, "250g": 12, "unit": "kg"},
        "potatoes": {"1kg": 35, "500g": 20, "unit": "kg"},
        "potato": {"1kg": 35, "500g": 20, "unit": "kg"},
        "mixed vegetables": {"1kg": 80, "500g": 45, "unit": "kg"},
        "carrot": {"1kg": 50, "500g": 28, "unit": "kg"},
        "beans": {"1kg": 60, "500g": 35, "unit": "kg"},
        "capsicum": {"1kg": 70, "500g": 38, "unit": "kg"},
        "cauliflower": {"1": 40, "unit": "piece"},
        "cabbage": {"1": 30, "unit": "piece"},
        "spinach": {"250g": 25, "bunch": 20, "unit": "bunch"},
        "palak": {"250g": 25, "bunch": 20, "unit": "bunch"},
        "garlic": {"250g": 20, "100g": 10, "unit": "kg"},
        "ginger": {"250g": 25, "100g": 12, "unit": "kg"},
        "green chillies": {"100g": 15, "250g": 30, "unit": "kg"},
        "lemon": {"1": 5, "4": 18, "unit": "piece"},
        "coriander": {"100g": 15, "bunch": 10, "unit": "bunch"},
        "mint": {"100g": 15, "bunch": 10, "unit": "bunch"},
        "curry leaves": {"50g": 10, "unit": "bunch"},
        "yogurt": {"500g": 35, "200g": 18, "400g": 30, "unit": "kg"},
        "curd": {"500g": 35, "200g": 18, "400g": 30, "unit": "kg"},
        "milk": {"1l": 60, "500ml": 32, "unit": "l"},
        "ghee": {"500ml": 350, "200ml": 150, "100ml": 80, "unit": "l"},
        "butter": {"100g": 55, "500g": 260, "unit": "kg"},
        "oil": {"1l": 150, "500ml": 80, "100ml": 18, "unit": "l"},
        "sunflower oil": {"1l": 150, "unit": "l"},
        "turmeric": {"100g": 30, "unit": "kg"},
        "chilli powder": {"100g": 40, "unit": "kg"},
        "coriander powder": {"100g": 35, "unit": "kg"},
        "garam masala": {"100g": 50, "50g": 28, "unit": "kg"},
        "biryani masala": {"50g": 35, "100g": 65, "packet": 35, "unit": "packet"},
        "chicken masala": {"50g": 35, "unit": "packet"},
        "dal": {"1kg": 120, "500g": 65, "250g": 35, "unit": "kg"},
        "toor dal": {"1kg": 120, "500g": 65, "250g": 35, "unit": "kg"},
        "moong dal": {"1kg": 130, "500g": 70, "unit": "kg"},
        "chana dal": {"1kg": 110, "500g": 60, "unit": "kg"},
        "rajma": {"1kg": 140, "500g": 75, "unit": "kg"},
        "chickpeas": {"1kg": 130, "500g": 70, "unit": "kg"},
        "coconut": {"1": 40, "unit": "piece"},
        "tamarind": {"250g": 50, "unit": "kg"},
        "jaggery": {"500g": 60, "unit": "kg"},
        "salt": {"1kg": 25, "unit": "kg"},
        "sugar": {"1kg": 50, "unit": "kg"},
    }
    
    clean_name = item_name.lower()
    value, unit = parse_quantity(qty_str)
    
    for key, price_dict in base_prices.items():
        if key in clean_name:
            if qty_str in price_dict:
                return price_dict[qty_str]
            
            base_unit = price_dict.get("unit", "kg")
            
            if "kg" in unit or unit == "kg":
                if "1kg" in price_dict:
                    return int(price_dict["1kg"] * value)
                elif "500g" in price_dict:
                    return int(price_dict["500g"] * value * 2)
            elif "g" in unit:
                if "500g" in price_dict and value == 500:
                    return price_dict["500g"]
                elif "250g" in price_dict and value == 250:
                    return price_dict["250g"]
                elif "100g" in price_dict and value == 100:
                    return price_dict["100g"]
                elif "1kg" in price_dict:
                    return int(price_dict["1kg"] * (value / 1000))
            elif "ml" in unit or unit == "l":
                if "1l" in price_dict and unit == "l":
                    return int(price_dict["1l"] * value)
                elif "500ml" in price_dict and value == 500:
                    return price_dict["500ml"]
                elif "100ml" in price_dict and value == 100:
                    return price_dict["100ml"]
            elif "packet" in unit:
                return price_dict.get("packet", 50)
            elif "piece" in unit or "pieces" in unit:
                if str(int(value)) in price_dict:
                    return price_dict[str(int(value))]
            
            return list(price_dict.values())[0]
    
    if "kg" in unit:
        return int(100 * value)
    elif "g" in unit:
        return int(100 * (value / 1000))
    elif "ml" in unit or "l" in unit:
        return int(150 * value) if unit == "l" else int(150 * (value / 1000))
    return 50

# ============================================
# MAIN AGENT FUNCTION
# ============================================
def ask_agent(user_question, stream=False):
    client = get_client()
    
    is_food, reason = is_food_request(user_question, client)
    
    if not is_food:
        if reason == "GREETING":
            response = "Hi! I'm Smart Cart Agent. Ask me for food recipe ingredients.\n\nExamples:\n- Mutton biryani for 2\n- Palak paneer\n- Weekly vegetables list\n- Dal tadka"
        else:
            response = "Sorry, I can only help with food recipes & grocery ingredients.\n\nTry: 'Chicken curry' or 'Veg pulao' or 'Rajma chawal'"
        
        if stream:
            for word in response.split():
                yield word + " "
        else:
            return response
        return
    
    items_text = google_search_any_recipe(user_question, client)
    
    items_list = []
    item_details = {}
    for line in items_text.split('\n'):
        line = line.strip()
        if line and len(line) > 2:
            qty_match = re.search(r'(\d+\s*(?:kg|g|ml|l|packet|piece|pieces|bunch|tbsp|tsp|unit)s?)$', line, re.IGNORECASE)
            qty = qty_match.group(1) if qty_match else "1 unit"
            name = re.sub(r'\s+\d+\s*(?:kg|g|ml|l|packet|piece|pieces|bunch|tbsp|tsp|unit)s?$', '', line, flags=re.IGNORECASE).strip()
            if len(name) >= 2:
                items_list.append(name)
                item_details[name] = {"qty": qty}
    
    if len(items_list) < 4:
        dish_prompt = f"Extract main dish name from: '{user_question}'"
        dish_resp = client.chat.completions.create(
            messages=[{"role": "user", "content": dish_prompt}],
            model="llama-3.1-8b-instant", temperature=0.1,
        )
        dish_name = dish_resp.choices[0].message.content.strip()
        
        complete_prompt = f"""Complete the ingredient list for "{dish_name}". 
Current items: {', '.join(items_list)}
User request: {user_request}

Add missing main ingredients to make total 4-6 items.
Output ONLY the additional items, one per line with quantity:"""

        complete_resp = client.chat.completions.create(
            messages=[{"role": "user", "content": complete_prompt}],
            model=get_working_model(), temperature=0.3,
        )
        
        for line in complete_resp.choices[0].message.content.split('\n'):
            line = line.strip()
            if line and len(items_list) < 6:
                qty_match = re.search(r'(\d+\s*\w+)$', line)
                qty = qty_match.group(1) if qty_match else "1 unit"
                name = re.sub(r'\s+\d+\s*\w+$', '', line).strip()
                if len(name) >= 2 and name not in items_list:
                    items_list.append(name)
                    item_details[name] = {"qty": qty}
    
    final_items = []
    for name in items_list[:6]:
        qty = item_details.get(name, {}).get('qty', '1 unit')
        price = get_blinkit_price(name, qty)
        url = mcp_blinkit_search_tool(name)
        final_items.append({
            "name": name, "qty": qty, "price": price, "url": url
        })
    
    table_lines = [f"{i['name']} | {i['qty']} | ₹{i['price']}" for i in final_items]
    table_str = "\n".join(table_lines)
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "Create markdown table with headers Item|Quantity|Approx Price (INR) and add Total row. Output only table."},
            {"role": "user", "content": f"Create table for:\n{table_str}"}
        ],
        model=get_working_model(), temperature=0.3,
    )
    table = response.choices[0].message.content
    
    cart_data_parts = [f"{i['name']}||{i['qty']}||{i['price']}||{i['url']}" for i in final_items]
    cart_data_string = ",,".join(cart_data_parts)
    final = f"{table}\n\n[CART_DATA]{cart_data_string}"
    
    if stream:
        for word in final.split():
            yield word + " "
    else:
        return final

__all__ = ['ask_agent', 'mcp_blinkit_search_tool']
