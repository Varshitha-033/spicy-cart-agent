import streamlit as st
from groq import Groq

def get_client():
    """Groq client lazy ga create cheyyali"""
    if "GROQ_API_KEY" not in st.secrets:
        st.error("GROQ_API_KEY secret ledu! Streamlit Cloud → Settings → Secrets lo add chey")
        st.stop()
    
    api_key = str(st.secrets["GROQ_API_KEY"]).strip().replace('\n','').replace('\r','')
    
    if len(api_key)!= 56:
        st.error(f"GROQ_API_KEY length tappu! 56 undali, kani {len(api_key)} undi. Extra space/line check chey.")
        st.stop()
        
    return Groq(api_key=api_key)

def get_working_model():
    """Available model nundi best dhi select cheyyali"""
    client = get_client()
    try:
        models = client.models.list().data
        preferred = [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192", 
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant"
        ]
        available_ids = [m.id for m in models]
        for model in preferred:
            if model in available_ids:
                return model
        return available_ids[0]
    except Exception:
        return "llama-3.1-8b-instant"

def ask_agent(user_question, stream=False):
    """Agent tho matladadam"""
    client = get_client()
    messages = [
        {
            "role": "system",
            "content": """You are 'Spicy Cart Agent'. For recipe/shopping questions:
1. Give a markdown table with columns: Item | Quantity | Approx Price (INR)
2. Calculate total at the end
3. End response with [CART_DATA]item:qty:price,item:qty:price,... for parsing
4. Keep prices realistic for Indian markets
5. Don't include 'Total' row in CART_DATA"""
        },
        {"role": "user", "content": user_question}
    ]

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=get_working_model(),
        temperature=0.7,
        stream=stream,
    )

    if stream:
        for chunk in chat_completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        return chat_completion.choices[0].message.content
