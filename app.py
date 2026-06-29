import streamlit as st
import re
from backend import ask_agent

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒")
st.title("🛒 Smart Cart Agent - Price Compare")
st.caption("ADK Multi-Agent: Finds cheapest price across Blinkit, Flipkart, Amazon, Meesho")

if "messages" not in st.session_state:
    st.session_state.messages = []

def parse_cart_data(text):
    """Extract items with platform and URL from CART_DATA"""
    cart_data = []
    seen_items = set()
    
    cart_match = re.search(r'\[CART_DATA\](.*)', text, re.DOTALL)
    if cart_match:
        cart_string = cart_match.group(1).strip()
        items = cart_string.split(',')
        
        for item in items:
            parts = item.split(':')
            # FIX: Now expecting 5 parts - name:qty:price:platform:url
            if len(parts) >= 5:
                name = parts[0].strip()
                generic_names = ['item', 'product', 'grocery', 'total', 'items', '']
                if name.lower() in generic_names or len(name) < 2:
                    continue
                
                if name.lower() in seen_items:
                    continue
                seen_items.add(name.lower())
                
                cart_data.append({
                    "name": name,
                    "qty": parts[1].strip(),
                    "price": parts[2].strip(),
                    "platform": parts[3].strip(),
                    "url": parts[4].strip()
                })
    return cart_data

def show_best_price_buttons(cart_data):
    """UI: Show button with platform name and price"""
    if not cart_data:
        st.warning("No specific items found. Try: 'chicken biryani' or 'cotton kurti'")
        return
        
    st.markdown("---")
    st.markdown("### 💰 Best Prices Found")
    st.caption("Powered by 4 MCP Tools: Blinkit, Flipkart, Amazon, Meesho")
    
    cols = st.columns(3)
    for idx, item in enumerate(cart_data):
        with cols[idx % 3]:
            label = f"{item['name']}\n₹{item['price']} on {item['platform']}"
            st.link_button(label, item['url'], use_container_width=True)

# Chat UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cart_data" in message and message["cart_data"]:
            show_best_price_buttons(message["cart_data"])

if prompt := st.chat_input("Chicken biryani for 4, or Cotton kurtis for girls..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("ADK Agents: Searching 4 platforms for best prices..."):
            for chunk in ask_agent(prompt, stream=True):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")
        
        cart_data = parse_cart_data(full_response)
        display_response = re.sub(r'\[CART_DATA\].*', '', full_response, flags=re.DOTALL).strip()
        message_placeholder.markdown(display_response)
        show_best_price_buttons(cart_data)
        
    st.session_state.messages.append({
        "role": "assistant", 
        "content": display_response,
        "cart_data": cart_data
    })

st.markdown("---")
st.caption("🔒 Security: No user data stored. Prices are simulated for demo. Multi-agent ADK + MCP architecture.")
