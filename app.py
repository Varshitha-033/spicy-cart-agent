import streamlit as st
import re
from backend import ask_agent, mcp_blinkit_search_tool

st.set_page_config(page_title="Smart Cart Agent - Food Only", page_icon="🛒")
st.title("🛒 Smart Cart Agent")
st.caption("Food & Recipe Ingredients Only | Powered by Blinkit")

if "messages" not in st.session_state:
    st.session_state.messages = []

def parse_cart_data(text):
    """Extract food items with Blinkit URL from CART_DATA"""
    cart_data = []
    seen_items = set()

    cart_match = re.search(r'\[CART_DATA\](.*)', text, re.DOTALL)
    if cart_match:
        cart_string = cart_match.group(1).strip()
        items = cart_string.split(',')

        for item in items:
            parts = item.split(':')
            # Format: name:qty:price:url
            if len(parts) >= 4:
                name = parts[0].strip()
                if name.lower() in ['item', 'ingredient', 'total', ''] or len(name) < 2:
                    continue

                if name.lower() in seen_items:
                    continue
                seen_items.add(name.lower())

                cart_data.append({
                    "name": name,
                    "qty": parts[1].strip(),
                    "price": parts[2].strip(),
                    "url": parts[3].strip()
                })
    return cart_data

def show_blinkit_buttons(cart_data):
    """UI: Show Blinkit button for each ingredient"""
    if not cart_data:
        return

    st.markdown("---")
    st.markdown("### 🛒 Add to Blinkit Cart")
    st.caption("Powered by MCP Server Tool: blinkit_search")

    cols = st.columns(3)
    for idx, item in enumerate(cart_data):
        with cols[idx % 3]:
            label = f"{item['name']}\n₹{item['price']}"
            st.link_button(label, item['url'], use_container_width=True)

# Chat UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cart_data" in message and message["cart_data"]:
            show_blinkit_buttons(message["cart_data"])

if prompt := st.chat_input("Chicken biryani for 4, or Weekly vegetables..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with st.spinner("ADK Agents: Finding ingredients..."):
            for chunk in ask_agent(prompt, stream=True):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")

        cart_data = parse_cart_data(full_response)
        display_response = re.sub(r'\[CART_DATA\].*', '', full_response, flags=re.DOTALL).strip()
        message_placeholder.markdown(display_response)

        if cart_data:
            show_blinkit_buttons(cart_data)

    st.session_state.messages.append({
        "role": "assistant",
        "content": display_response,
        "cart_data": cart_data
    })

st.markdown("---")
st.caption("🔒 Security: No user data stored. Food & grocery only. API keys secured.")
