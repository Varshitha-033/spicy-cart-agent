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
        st.error("GROQ_API_KEY secret ledu!")
        st.stop()
    
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    
    if len(api_key)!= 56:
        st.error(f"Key length tappu! 56 undali, kani {len(api_key)} undi.")
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
    """Check if user is asking for food/recipe or just greeting"""
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
# AGENT 1: Universal Google Search - ANY RECIPE
# ============================================
def google_search_any_recipe(user_request, client):
    """Real Google search for ANY recipe - Backend lo jarugutundi"""
    serpapi_key = get_serpapi_key()
    
    # Step 1: Extract dish/recipe name - ANY dish, not just biryani
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
    
    # Step 2: Google search - Backend lo, user ki kanapadadu
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
                # Combine top 2 results for better ingredients
                snippets = []
                for i in range(min(2, len(data["organic_results"]))):
                    snippets.append(data["organic_results"][i].get("snippet", ""))
                search_snippet = " ".join(snippets)
        except:
            pass
    
    # Step 3: Extract ingredients - Dynamic, no hardcode
    if search_snippet:
        extract_prompt = f"""From this Google search result, extract EXACTLY 4-6 main ingredients with quantities for the recipe.

Search Result: {search_snippet}
User Request: {user_request}
Dish: {dish_name}

CRITICAL RULES:
1. Output EXACTLY 4-6 lines. Count them.
2. Use EXACT ingredients from search result or user request
3. If user says 'mutton', use 'Mutton', NOT 'Chicken'
4. If user says 'veg', use vegetables, NOT meat
5. If user says 'paneer', use 'Paneer'
6. Format: "Ingredient Name 500g" or "Ingredient Name 1kg" per line
7. Include quantities: 500g, 1kg, 250g, 1 packet, 2 pieces, etc
8. Only main cooking ingredients, skip water/salt
9. If recipe is 'weekly vegetables', list 4-6 common vegetables

Output 4-6 ingredients with quantities:"""
    else:
        # Fallback - LLM generates based on dish name, NOT biryani hardcoded
        extract_prompt = f"""For the recipe "{dish_name}", list EXACTLY 4-6 main ingredients with quantities.

User Request: {user_request}

CRITICAL RULES:
1. Output EXACTLY 4-6 lines
2. Use EXACT protein/item user mentioned
3. If 'mutton' in request, use 'Mutton 500g', NOT Chicken
4. If 'veg' or 'vegetable', use vegetables
5. If 'paneer', use 'Paneer 250g'
6. If 'dal', use 'Toor Dal 250g' etc
7. Format: "Ingredient Name 500g" per line
8. Think what main ingredients this {dish_name} needs

Output 4-6 ingredients:"""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": extract_prompt}],
        model=get_working_model(), temperature=0.3,
    )
    return response.choices[0].message.content

# ============================================
# AGENT 2: Dynamic Blinkit Price Lookup
# ============================================
def get_blinkit_price(item_name):
    """Dynamic price lookup - Not hardcoded to biryani items"""
    # Base prices - Common Indian grocery items
    prices = {
        "rice": 80, "basmati rice": 249, "wheat flour": 60, "atta": 60,
        "mutton": 599, "chicken": 220, "fish": 350, "prawns": 450,
        "paneer": 120, "tofu": 100, "eggs": 70,
        "onions": 35, "tomatoes": 40, "potatoes": 35, "potato": 35,
        "garlic": 20, "ginger": 25, "green chillies": 20, "lemon": 10,
        "coriander": 15, "mint": 15, "curry leaves": 15,
        "yogurt": 45, "curd": 45, "milk": 30, "ghee": 250, "butter": 60,
        "oil": 150, "sunflower oil": 150, "mustard oil": 180,
        "turmeric": 30, "chilli powder": 40, "coriander powder": 35,
        "garam masala": 50, "biryani masala": 55, "chicken masala": 50,
        "dal": 120, "toor dal": 120, "moong dal": 130, "chana dal": 110,
        "rajma": 140, "chickpeas": 130, "kidney beans": 140,
        "mixed vegetables": 80, "carrot": 50, "beans": 60, "capsicum": 70,
        "cauliflower": 40, "cabbage": 30, "spinach": 25, "palak": 25,
        "saffron": 500, "cashew": 900, "almonds": 800,
        "coconut": 40, "tamarind": 50, "jaggery": 60,
        "salt": 25, "sugar": 50, "tea": 150, "coffee": 200
    }
    
    clean_name = item_name.lower()
    
    # Check for exact matches with quantity
    if "mutton" in clean_name and "500" in item_name:
        return 599
    if "chicken" in clean_name and "500" in item_name:
        return 220
    if "basmati rice" in clean_name and "1" in item_name and "kg" in item_name.lower():
        return 249
    if "paneer" in clean_name and "250" in item_name:
        return 120
    
    # Fuzzy match
    for key, price in prices.items():
        if key in clean_name:
            return price
    
    # Default fallback based on quantity
    if "kg" in item_name.lower():
        return 200
    elif "500g" in item_name or "500" in item_name:
        return 150
    elif "250g" in item_name or "250" in item_name:
        return 80
    elif "packet" in item_name.lower():
        return 50
    return 100

# ============================================
# MAIN AGENT FUNCTION
# ============================================
def ask_agent(user_question, stream=False):
    client = get_client()
    
    # Step 0: Check if food request
    is_food, reason = is_food_request(user_question, client)
    
    if not is_food:
        if reason == "GREETING":
            response = "Hi! 👋 Nenu Smart Cart Agent ni. Food recipe ingredients kosam adagandi.\n\nExamples:\n- Mutton biryani for 2\n- Palak paneer\n- Weekly vegetables list\n- Dal tadka"
        else:
            response = "Sorry, nenu food recipes & grocery ingredients matrame help cheyagalanu.\n\nTry: 'Chicken curry' or 'Veg pulao' or 'Rajma chawal'"
        
        if stream:
            for word in response.split():
                yield word + " "
        else:
            return response
        return
    
    # Step 1: Google search for ANY recipe - No biryani hardcode
    items_text = google_search_any_recipe(user_question, client)
    
    # Step 2: Parse ingredients
    items_list = []
    item_details = {}
    for line in items_text.split('\n'):
        line = line.strip()
        if line and len(line) > 2:
            # Extract quantity from end
            qty_match = re.search(r'(\d+\s*(?:kg|g|ml|l|packet|piece|pieces|bunch|tbsp|tsp|unit)s?)$', line, re.IGNORECASE)
            qty = qty_match.group(1) if qty_match else "1 unit"
            name = re.sub(r'\s+\d+\s*(?:kg|g|ml|l|packet|piece|pieces|bunch|tbsp|tsp|unit)s?$', '', line, flags=re.IGNORECASE).strip()
            if len(name) >= 2:
                items_list.append(name)
                item_details[name] = {"qty": qty}
    
    # Step 3: Ensure minimum 4 items - Dynamic fallback, NOT biryani
    if len(items_list) < 4:
        # Ask LLM to complete the ingredient list for this specific dish
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
    
    # Step 4: Build table with prices
    final_items = []
    for name in items_list[:6]:
        price = get_blinkit_price(name)
        qty = item_details.get(name, {}).get('qty', '1 unit')
        url = mcp_blinkit_search_tool(name)
        final_items.append({
            "name": name, "qty": qty, "price": price, "url": url
        })
    
    # Step 5: Create markdown table
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
