import streamlit as st
from groq import Groq
from serpapi import GoogleSearch
import os

# ===== CONFIG =====
st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒")

# ===== PRICE FLOOR =====
MIN_PRICE_PER_PERSON = {
    "biryani": 150,
    "burger": 99,
    "pizza": 199,
    "meal": 120,
    "thali": 100,
    "sandwich": 80
}

def enforce_price_floor(item_name, api_price=None):
    """API price takkuva unna minimum price istadi"""
    item_lower = item_name.lower().strip()

    base_price = 100
    for food, min_val in MIN_PRICE_PER_PERSON.items():
        if food in item_lower:
            base_price = min_val
            break

    if api_price and isinstance(api_price, (int, float)) and api_price > 0:
        return max(api_price, base_price)
    else:
        return base_price

# ===== SERPAPI SEARCH =====
def search_grocery_price(item):
    try:
        params = {
            "q": f"{item} price India",
            "api_key": st.secrets["SERPAPI_KEY"],
            "engine": "google_shopping"
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        api_price = None
        if "shopping_results" in results and results["shopping_results"]:
            price_str = results["shopping_results"][0].get("price", "0")
            api_price = int(''.join(filter(str.isdigit, price_str[:6])))
    except:
        api_price = None

    final_price = enforce_price_floor(item, api_price)
    return final_price

# ===== GROQ DIRECT CALL - NO LANGCHAIN AGENTS =====
def get_agent_response(user_prompt, chat_history):
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # Price tool ni manual ga call cheddam
    price_info = ""
    for food in MIN_PRICE_PER_PERSON.keys():
        if food in user_prompt.lower():
            price = search_grocery_price(food)
            price_info += f"\n{food.title()} price: ₹{price} per person"

    system_msg = f"""
You are Smart Cart Agent for Indian families.

CRITICAL PRICING RULES:
1. Biryani = MINIMUM ₹150 per person
2. Burger = MINIMUM ₹99 per person
3. Pizza = MINIMUM ₹199 per person
4. Never quote below these prices

Current price data: {price_info}

Help user plan grocery meals. Give breakdown with totals.
"""

    messages = [{"role": "system", "content": system_msg}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_prompt})

    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        temperature=0.3
    )
    return response.choices[0].message.content

# ===== STREAMLIT UI - NEE OLD UI SAME =====
st.title("🛒 Smart Cart Agent - AI Grocery Planner")
st.caption("Kaggle Capstone 2026")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask: '1 person biryani meal plan'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Finding best prices..."):
            # Last 6 messages history pass chey
            history = st.session_state.messages[-6:]
            response = get_agent_response(prompt, history)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# ===== SIDEBAR =====
with st.sidebar:
    st.header("💰 Base Prices")
    st.caption("Minimum per person")
    for item, price in MIN_PRICE_PER_PERSON.items():
        st.markdown(f"**{item.title()}**: ₹{price}")

    st.divider()
    st.caption("Kaggle AI Agents Capstone 2026")
