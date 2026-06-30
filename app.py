import streamlit as st
from groq import Groq
import urllib.parse

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80
}

# ===== DEFAULT INGREDIENTS WITH SCALING =====
INGREDIENTS_MAP = {
    "biryani": {
        "Basmati Rice": {"base": 250, "unit": "g"},
        "Chicken": {"base": 250, "unit": "g"},
        "Biryani Masala": {"base": 1, "unit": "packet"},
        "Onions": {"base": 150, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Ghee": {"base": 50, "unit": "ml"}
    },
    "burger": {
        "Burger Buns": {"base": 1, "unit": "pc"},
        "Chicken Patty": {"base": 1, "unit": "pc"},
        "Cheese Slices": {"base": 1, "unit": "pc"},
        "Lettuce": {"base": 20, "unit": "g"},
        "Tomato": {"base": 50, "unit": "g"},
        "Mayonnaise": {"base": 1, "unit": "packet"}
    },
    "pizza": {
        "Pizza Base": {"base": 1, "unit": "pc"},
        "Pizza Sauce": {"base": 1, "unit": "packet"},
        "Mozzarella Cheese": {"base": 100, "unit": "g"},
        "Capsicum": {"base": 50, "unit": "g"},
        "Onion": {"base": 50, "unit": "g"},
        "Sweet Corn": {"base": 50, "unit": "g"}
    },
    "thali": {
        "Rice": {"base": 200, "unit": "g"},
        "Toor Dal": {"base": 100, "unit": "g"},
        "Vegetables Mix": {"base": 200, "unit": "g"},
        "Curd": {"base": 100, "unit": "ml"},
        "Chapati Flour": {"base": 150, "unit": "g"}
    }
}

def calculate_price(item, qty):
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item.lower():
            base_price = min_val
            break
    return base_price * int(qty)

def create_blinkit_cart_link(ingredients_list):
    query = ",".join(ingredients_list)
    encoded_query = urllib.parse.quote(query)
    return f"https://blinkit.com/s/?q={encoded_query}"

def get_scaled_ingredients(item, qty):
    """AI fail ayina manual ga scale chesi istadi"""
    base_items = INGREDIENTS_MAP.get(item.lower(), {})
    scaled_list = []
    search_items = []

    for ing, data in base_items.items():
        scaled_qty = data["base"] * qty
        unit = data["unit"]
        # Round to nice numbers
        if unit == "g" and scaled_qty >= 1000:
            scaled_list.append(f"{ing} - {scaled_qty/1000:.1f}kg")
        elif unit == "ml" and scaled_qty >= 1000:
            scaled_list.append(f"{ing} - {scaled_qty/1000:.1f}L")
        else:
            scaled_list.append(f"{ing} - {int(scaled_qty)}{unit}")

        search_items.append(ing)

    return scaled_list, search_items

def get_ai_ingredients(item, qty):
    """Groq tho try chey, fail aithe None return"""
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        prompt = f"""For {qty} person {item}, list ingredients with quantity.
Format: Item - Quantity
No extra text. Indian portions."""

        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400
        )
        return response.choices[0].message.content
    except:
        return None

# ===== UI =====
st.title("🛒 Smart Cart Agent")
st.subheader("Ingredients List + Blinkit Cart Link Generator")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    item = st.selectbox("Select Meal", options=list(MIN_PRICE_PER_PERSON.keys()), format_func=lambda x: x.title())

with col2:
    qty = st.number_input("People", min_value=1, max_value=20, value=2)

with col3:
    st.write("")
    generate_btn = st.button("Generate Cart 🛍️", use_container_width=True, type="primary")

if generate_btn:
    total = calculate_price(item, qty)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Meal", item.title())
    with c2:
        st.metric("People", qty)
    with c3:
        st.metric("Min Total", f"₹{total}")

    st.divider()
    st.subheader("📝 Ingredients List")

    # Try AI first, fallback to manual scaling
    ai_result = get_ai_ingredients(item, qty)

    if ai_result:
        st.code(ai_result, language=None)
        # Extract for blinkit
        ingredients_for_link = []
        for line in ai_result.split('\n'):
            if '-' in line:
                ingredients_for_link.append(line.split('-')[0].strip())
    else:
        st.warning("AI failed. Using calculated portions.")
        scaled_list, ingredients_for_link = get_scaled_ingredients(item, qty)
        for ing in scaled_list:
            st.write(f"- {ing}")

    # Blinkit Link - AI fail ayina vastadi
    if ingredients_for_link:
        cart_link = create_blinkit_cart_link(ingredients_for_link[:8])
        st.success("✅ Cart Ready!")
        st.link_button(
            "🛍️ Add All to Blinkit Cart",
            cart_link,
            use_container_width=True,
            type="primary"
        )
        st.caption(f"Search includes: {', '.join(ingredients_for_link[:6])}...")

# ===== SIDEBAR =====
with st.sidebar:
    st.header("💰 Base Prices")
    for food, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{food.title()}**: ₹{price}/person")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
