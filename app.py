import streamlit as st
import re
from backend import ask_agent, mcp_blinkit_search_tool

# ============================================
# SMART CART AGENT - Kaggle Capstone Project
# Track: Concierge Agents
# Concepts Used: 
# 1. Google ADK Multi-Agent System
# 2. MCP Server Tools 
# 3. Security Features
# 4. Deployability
# ============================================

st.set_page_config(page_title="Smart Cart Agent", page_icon="🛒")
st.title("🛒 Smart Cart Agent")
st.caption("ADK-powered shopping assistant. Ask for any list - recipes, party, groceries")

if "messages" not in st.session_state:
    st.session_state.messages = []

def parse_cart_data(text):
    """
    Extract items from CART_DATA tag. 
    Security: Filters generic/duplicate/empty items
    """
    cart_data = []
    seen_items = set()
    
    cart_match = re.search(r'\[CART_DATA\](.*)', text, re.DOTALL)
    if cart_match:
        cart_string = cart_match.group(1).strip()
        items = cart_string.split(',')
        
        for item in items:
            parts = item.split(':')
            if len(parts) >= 2:
                name = parts[0].strip()
                name = re.sub(r'\s*\(.*?\)', '', name).strip()
                
                # FILTER: Skip generic names and 'Total'
                generic_names = ['item', 'product', 'grocery', 'ingredient', 'total', 'items', '']
                if name.lower() in generic_names or len(name) < 2:
                    continue
                
                # FILTER: Skip duplicates
                if name.lower() in seen_items:
                    continue
                seen_items.add(name.lower())
                
                cart_data.append({
                    "name": name,
                    "qty": parts[1].strip(),
                    "price": parts[2].strip() if len(parts) > 2 else "0"
                })
    return cart_data

def show_blinkit_buttons(cart_data):
    """
    UI Component: Uses MCP Tool for link generation
    Powered by MCP Server Tool: blinkit_search
    """
    if not cart_data:
        st.warning("No specific items found. Please try a more detailed request.")
        return
        
    st.markdown("---")
    st.markdown("### 🛒 Add to Blinkit")
    st.caption("Powered by MCP Server Tool: blinkit_search")
    
    cols = st.columns(3)
    for idx, item in enumerate(cart_data):
        blinkit_url = mcp_blinkit_search_tool(item["name"])
        with cols[idx % 3]:
            st.link_button(f"{item['name']}", blinkit_url, use_container_width=True)

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "cart_data" in message and message["cart_data"]:
            show_blinkit_buttons(message["cart_data"])

# Chat input
if prompt := st.chat_input("Chicken biryani for 4, or Monthly toiletries..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # ADK Multi-Agent Pipeline runs here
        with st.spinner("ADK Agents working: Parser -> Pricer -> Compiler..."):
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

# Security Footer
st.markdown("---")
st.caption("🔒 Security: No user data stored. API keys secured in Streamlit secrets. Input sanitization active.")
