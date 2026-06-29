import streamlit as st
import re
from backend import ask_agent

st.set_page_config(page_title="Spicy Cart Agent", page_icon="🛒")
st.title("🛒 Spicy Cart Agent")
st.caption("Recipe adugu, budget list + cart istha!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Old messages display
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Manchi biryani recipe 4 mandiki..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Stream response
        for chunk in ask_agent(prompt, stream=True):
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")
        
        # [CART_DATA] hide cheyyali
        display_response = re.sub(r'\[CART_DATA\].*', '', full_response, flags=re.DOTALL).strip()
        message_placeholder.markdown(display_response)
        
    st.session_state.messages.append({"role": "assistant", "content": display_response})
