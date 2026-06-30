import streamlit as st
from groq import Groq
import re

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒", layout="wide")

# ===== PRICE FLOOR =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80,
    "dosa": 60,
    "idli": 40,
    "roll": 90
}

def calculate_price(item, qty):
    item_lower = item.lower().strip()
    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break
    return base_price * int(qty)

# ===== GROQ FOR MEAL SUGGESTIONS =====
def get_meal_suggestion(item, qty, budget=None):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    prompt = f"""You are Smart Cart Agent.

User wants: {qty} person {item}
Base price: ₹{MIN_PRICE_PER_PERSON.get(item.lower(), 100)} per person
Total: ₹{calculate_price(item, qty)}

Give:
1. Breakdown of items needed from Blinkit
2. Estimated quantities
3. Total cost must be minimum ₹{calculate_price(item, qty)}
4. Keep it under 4 lines

Indian context. No extra text."""

    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=300
    )
    return response.choices[0].message.content

# ===== NEW UI - FORM BASED =====
st.title("🛒 Smart Cart Agent")
st.subheader("Instant Grocery Price Calculator for Indian Meals")

# Input Section
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    item = st.selectbox(
        "Select Item",
        options=list(MIN_PRICE_PER_PERSON.keys()),
        index=0,
        format_func=lambda x: x.title()
    )

with col2:
    qty = st.number_input("People", min_value=1, max_value=20, value=1, step=1)

with col3:
    st.write("") # spacing
    st.write("")
    calc_btn = st.button("Get Price 💰", use_container_width=True, type="primary")

# Result Section
if calc_btn:
    total = calculate_price(item, qty)

    st.divider()

    # Big Price Display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Item", value=item.title())
    with col2:
        st.metric(label="Quantity", value=f"{qty} Person")
    with col3:
        st.metric(label="Total Price", value=f"₹{total}", delta=f"₹{total//qty}/person")

    st.divider()

    # AI Meal Plan
    with st.spinner("Creating meal plan..."):
        try:
            suggestion = get_meal_suggestion(item, qty)
            st.success("**Meal Plan:**")
            st.write(suggestion)
        except Exception as e:
            st.warning(f"AI suggestion failed. Base price: ₹{total}")
            st.code(f"{item.title()} x {qty} = ₹{total}")

    # Blinkit Link
    st.link_button(
        "🛍️ Open Blinkit & Order",
        f"https://blinkit.com/s/?q={item}",
        use_container_width=True
    )

# ===== SIDEBAR - PRICE TABLE =====
with st.sidebar:
    st.header("📋 Price Chart")
    st.caption("Minimum rates per person")

    # Table format
    data = []
    for food, price in MIN_PRICE_PER_PERSON.items():
        data.append({"Item": food.title(), "Min Price": f"₹{price}"})

    st.dataframe(data, use_container_width=True, hide_index=True)

    st.divider()
    st.info("**Rules:**\n- Biryani: ₹150+\n- Burger: ₹99+\n- Pizza: ₹199+\n- All prices per person")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")

# ===== FOOTER CARDS =====
st.divider()
st.subheader("Popular Combos")
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("2 Biryani", use_container_width=True):
        st.session_state.combo = ("biryani", 2)
        st.rerun()
with c2:
    if st.button("1 Burger", use_container_width=True):
        st.session_state.combo = ("burger", 1)
        st.rerun()
with c3:
    if st.button("3 Pizza", use_container_width=True):
        st.session_state.combo = ("pizza", 3)
        st.rerun()
with c4:
    if st.button("4 Thali", use_container_width=True):
        st.session_state.combo = ("thali", 4)
        st.rerun()

# Handle combo clicks
if "combo" in st.session_state:
    item, qty = st.session_state.combo
    total = calculate_price(item, qty)
    st.success(f"**{item.title()} x {qty} = ₹{total}**")
    del st.session_state.combo
