import streamlit as st
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_working_model():
    """Available models lo okati auto select chestadi"""
    try:
        models = client.models.list().data
        # Priority order - idi unte ide vadutham
        preferred = [
            "llama-3.3-70b-versatile",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant",
            "gemma2-9b-it"
        ]
        available_ids = [m.id for m in models]

        for model in preferred:
            if model in available_ids:
                print(f"Using model: {model}")
                return model

        # Okavela painavi lev ante, first available model teesko
        if available_ids:
            print(f"Using fallback model: {available_ids[0]}")
            return available_ids[0]
        else:
            raise Exception("No models available in your Groq account")
    except Exception as e:
        print(f"Error fetching models: {e}")
        return "llama-3.1-8b-instant" # Last fallback

def ask_agent(user_question, stream=False):
    messages = [
        {
            "role": "system",
            "content": "You are 'Spicy Cart Agent'. For recipe questions, give markdown table with Item, Quantity, Approx Price (INR). End with [CART_DATA]item:qty:price,..."
        },
        {"role": "user", "content": user_question}
    ]

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=get_working_model(), # Auto model selection
        temperature=0.7,
        stream=stream,
    )

    if stream:
        for chunk in chat_completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        return chat_completion.choices[0].message.content
