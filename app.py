import streamlit as st
import pandas as pd
from backend import ask_agent
import urllib.parse

# Page configuration
st.set_page_config(
    page_title="Spicy Cart Agent",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS for aesthetic theme
st.markdown("""
<style>
 .stApp {
        background-color: #0E1117;
    }
    h1 {
        color: #FF4B4B!important;
        text-align: center;
        font-weight: 700;
    }
 .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }
 .stButton>button:hover {
        background-color: #E03E3E;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛒 Spicy Cart Agent")
st.caption("Your Instant Recipe Budget Planner - Powered by Groq LPU")

st.subheader("What do you want to cook?")

question = st.text_input(
    "Enter your query",
    placeholder="Example: Chicken biryani recipe for 4 members with budget",
    label_visibility="collapsed"
)

if st.button("Generate Budget List", type="primary", use_container_width=True):
    if question:
        with st.spinner("Calculating your budget..."):
            response_placeholder = st.empty()
            full_response = ""
            for chunk in ask_agent(question, stream=True):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

            # Auto Cart Generator
            if "[CART_DATA]" in full_response:
                try:
                    cart_data = full_response.split("[CART_DATA]")[1].strip()
                    items = cart_data.split(",")
                    cart_list = []
                    total = 0

                    for item in items:
                        name, qty, price = item.split(":")
                        cart_list.append({
                            "Item": name.strip(),
                            "Quantity": qty.strip(),
                            "Price (₹)": price.strip()
                        })
                        total += int(price.strip())

                    st.write("---")
                    st.subheader("🛒 Your Cart is Ready")
                    st.dataframe(pd.DataFrame(cart_list), use_container_width=True, hide_index=True)
                    st.metric("Estimated Total Budget", f"₹ {total}")

                    # Demo cart link for Blinkit
                    cart_str = urllib.parse.quote(cart_data)
                    demo_link = f"https://blinkit.com/cart?items={cart_str}"
                    st.link_button("🛍️ Add to Blinkit Cart", demo_link, use_container_width=True)
                    st.caption("Note: This is a demo link. Real integration requires Blinkit API access.")

                except Exception as e:
                    st.error("Unable to parse cart data from response.")
    else:
        st.warning("Please enter a query first.")
