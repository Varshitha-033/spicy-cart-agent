"""
Smart Cart Agent - Streamlit UI
Concierge Agents Track - Kaggle Capstone Project
"""

import streamlit as st
from backend import CartAgent

# Page config
st.set_page_config(
    page_title="Smart Cart Agent",
    page_icon="🛒",
    layout="centered"
)

# Initialize Agent
agent = CartAgent()

# UI Header
st.title("🛒 Smart Cart Agent")
st.markdown("*Your AI Concierge for Indian Grocery Planning*")
st.markdown("---")

# Input Section
col1, col2 = st.columns([3, 1])

with col1:
    dish_input = st.text_input(
        "What do you want to cook?",
        placeholder="e.g., palak paneer, chicken biryani, sambar",
        key="dish"
    )

with col2:
    people_count = st.number_input(
        "People",
        min_value=1,
        max_value=20,
        value=1,
        key="people"
    )

# Generate Button
if st.button("🛍️ Generate Shopping List", type="primary", use_container_width=True):

    if not dish_input:
        st.warning("Please enter a dish name")
    elif agent.is_greeting(dish_input):
        st.info("👋 Hi! Tell me what dish you want to cook and for how many people. I'll create your complete shopping list with prices and Blinkit links!")
    else:
        with st.spinner("🤖 Agent is planning your shopping list..."):
            result = agent.generate_shopping_list(dish_input, people_count)

            if "items" in result and len(result["items"]) > 0:
                st.success(f"✅ Shopping list ready for {people_count} people!")

                # Display items with 4 columns
                st.subheader("📋 Your Shopping List")

                # Header row
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    st.markdown("**Item**")
                with col2:
                    st.markdown("**Qty**")
                with col3:
                    st.markdown("**Price**")
                with col4:
                    st.markdown("**Buy**")

                st.markdown("---")

                # Item rows
                for item in result["items"]:
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                    with col1:
                        st.write(f"**{item['item']}**")
                    with col2:
                        st.write(item['quantity'])
                    with col3:
                        st.write(f"₹{item['price_inr']}")
                    with col4:
                        st.link_button("🛒", item['blinkit_link'], help="Buy on Blinkit", use_container_width=True)

                st.markdown("---")

                # Total
                st.metric(
                    label="💰 Total Estimated Cost",
                    value=f"₹{result['total_inr']}",
                    delta=f"For {people_count} people"
                )

                # Show source
                if len(result["items"]) > 0:
                    st.caption(f"Prices from: {result['items'][0]['source']} | {result['agent_version']}")
                    st.caption("💡 Tip: Click 🛒 to buy directly on Blinkit")
            else:
                st.error("Could not generate list. Please try again with a different dish.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
Built for Kaggle AI Agents Intensive Capstone | Concierge Agents Track<br>
Agent Skills: Reasoning + Tool Use + Computation + Security + API Integration
</div>
""", unsafe_allow_html=True)
