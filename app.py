import streamlit as st
import re
import urllib.parse
from backend import ask_agent

st.set_page_config(page_title="Spicy Cart Agent", page_icon="🛒")
st.title("🛒 Spicy Cart Agent")
st.caption("Recipe adugu, Blinkit lo direct add chey!")

if "messages" not in st.session_state:
    st.session_state.messages = []

def parse_cart_data(text):
    """CART_DATA nundi items teeyadam"""
    cart_data = []
    cart_match = re.search(r'\[CART_DATA\](.*)', text, re.DOTALL)
    if cart_match:
        cart_string = cart_match.group(1).strip()
        items = cart_string.split(',')
        for item in items:
            parts = item.split(':')
            if len(parts) >= 2:
                name = parts[0].strip()
                name = re.sub(r'\s*\(.*?\)', '', name).strip()
                if name.lower()!= 'total':
                    cart_data.append({
                        "name": name,
                        "qty": parts[1].strip(),
                        "price": parts[2].strip() if len(parts) > 2 else "0"
                    })
    return cart_data

def show_blinkit_buttons(cart_data):
    """Blinkit buttons display cheyyadam"""
    if not cart_data:
        return
        
    st.markdown("---")
    st.markdown("### 🛒 Add to Blinkit")
    st.caption("Prati item button click chey → Blinkit lo open avtadi → Add kottey")
    
    cols = st.columns(3)
    for idx, item in enumerate(cart_data):
        search_query = urllib.parse.quote_plus(item["name"])
        blinkit_url = f"https://blinkit.com/s/?q={search_query}"
        with cols[idx % 3]:
            st.link_button(f"{item['name']}", blinkit_url, use_container_width=True)

# Old messages display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cart_data" in message and message["cart_data"]:
            show_blinkit_buttons(message["cart_data"])

# User input
if prompt := st.chat_input("Chicken biryani 4 mandiki..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        for chunk in ask_agent(prompt, stream=True):
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
        
        cart_data = parse_cart_data(full_response)
        display_response = re.sub(r'\[CART_DATA\].*', '', full_response, flags=re.DOTALL).strip()
        message_placeholder.markdown(display_response)
        show_blinkit_buttons(cart_data)
        
    st.session_state.messages.append({
        "role": "assistant", 
        "content": display_response,
        "cart_data": cart_data
    })
