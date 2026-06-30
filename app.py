# ===== PRICE FLOOR CONFIG =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99, 
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "roll": 90
}

# ===== MAIN PRICE FUNCTION =====
def calculate_item_price(item_name, qty=1, api_price=None):
    """
    Item ki minimum price enforce chestadi
    api_price: SerpAPI/Groq nunchi vachina price. None unte MIN_PRICE use avtadi
    """
    item_lower = item_name.lower().strip()
    
    # 1. Base price find chey - keyword match
    base_price = 0
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break
    
    # 2. API price unte, minimum tho compare chey
    if api_price and isinstance(api_price, (int, float)):
        final_price = max(api_price, base_price)  # Yekkuva undedi teesuko
    else:
        final_price = base_price if base_price > 0 else 100  # Default ₹100
    
    # 3. Quantity tho multiply chey
    total = final_price * qty
    return int(total)

# ===== AGENT PROMPT UPDATE =====
SYSTEM_PROMPT = """
You are Smart Cart Agent for Indian families.

PRICING RULES - VERY IMPORTANT:
1. Biryani minimum ₹150 per person. Never quote below this.
2. Burger minimum ₹99 per person. Never quote below this.  
3. Pizza minimum ₹199 per person.
4. For any meal plan, use these base rates even if search shows cheaper.
5. Always calculate total = base_price * number_of_people

Example: "2 people biryani" = 150 * 2 = ₹300 minimum.
"""

# ===== USAGE EXAMPLE - Agent lo ela call cheyalo =====
def get_meal_plan_response(user_query):
    # Nee existing SerpAPI/LangChain code
    items = extract_items(user_query)  # ["biryani", "burger"]
    people = extract_people(user_query)  # 2
    
    total_cost = 0
    breakdown = []
    
    for item in items:
        # API price teesko if undi
        api_price = search_price_online(item)  # nee function
        
        # Price floor apply chey
        item_total = calculate_item_price(item, qty=people, api_price=api_price)
        total_cost += item_total
        breakdown.append(f"{item.title()}: ₹{item_total}")
    
    return total_cost, breakdown
