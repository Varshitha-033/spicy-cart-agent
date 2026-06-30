"""
Smart Cart Agent - Concierge Agents Track
Kaggle AI Agents Intensive Vibe Coding Capstone
"""

import requests
import json
import re
from groq import Groq
import streamlit as st

# SECURITY: API keys loaded from environment/secrets with graceful fallback
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except KeyError:
    st.error("Missing GROQ_API_KEY. Add it in Streamlit Cloud → Settings → Secrets")
    st.stop()

try:
    SERP_KEY = st.secrets["SERPAPI_KEY"]
    SERP_ENABLED = True
except KeyError:
    SERP_KEY = None
    SERP_ENABLED = False # Silent fallback - no UI warning

class CartAgent:
    def __init__(self):
        self.llm = Groq(api_key=GROQ_KEY)
        self.search_endpoint = "https://serpapi.com/search"
        self.serp_enabled = SERP_ENABLED
        # Removed st.info - no UI warning now

    def generate_shopping_list(self, dish: str, people: int) -> dict:
        dish = self._sanitize_input(dish)
        people = max(1, min(people, 20))
        ingredients = self._reason_ingredients(dish, people)
        priced_items = self._use_search_tool(ingredients)
        return self._calculate_total(priced_items, people)

    def _sanitize_input(self, dish: str) -> str:
        dish = dish.strip()[:100]
        dish = re.sub(r'[<>{}[\]\\]', '', dish)
        return dish

    def _reason_ingredients(self, dish: str, people: int) -> list:
        prompt = f"""List ALL ingredients needed for "{dish}" to serve {people} people.
Format: "ingredient - quantity unit" per line. No explanations."""
        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            raw_list = response.choices[0].message.content.strip()
            return [line.strip() for line in raw_list.split('\n') if line.strip() and '-' in line]
        except Exception as e:
            return [f"Error: {str(e)}"]

    def _use_search_tool(self, ingredients: list) -> list:
        priced_items = []
        for item_line in ingredients:
            try:
                parts = item_line.split('-')
                if len(parts) < 2:
                    continue
                ingredient = parts[0].strip()
                quantity = parts[1].strip()

                if self.serp_enabled:
                    price_data = self._fetch_price_from_web(ingredient)
                else:
                    # Silent fallback to estimated prices
                    price_data = {"price": self._estimate_price(ingredient), "source": "Estimated"}

                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "price_inr": price_data["price"],
                    "source": price_data["source"]
                })
            except:
                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "price_inr": 50,
                    "source": "Estimated"
                })
        return priced_items

    def _fetch_price_from_web(self, ingredient: str) -> dict:
        if not self.serp_enabled:
            return {"price": self._estimate_price(ingredient), "source": "Estimated"}

        params = {
            "q": f"{ingredient} price Blinkit India",
            "api_key": SERP_KEY,
            "engine": "google",
            "gl": "in"
        }
        try:
            response = requests.get(self.search_endpoint, params=params, timeout=5)
            data = response.json()
            if "organic_results" in data:
                for result in data["organic_results"][:3]:
                    price_match = re.search(r'₹\s*(\d+)', result.get("snippet", ""))
                    if price_match:
                        return {"price": int(price_match.group(1)), "source": "Blinkit/Zepto"}
        except:
            pass
        return {"price": self._estimate_price(ingredient), "source": "Estimated"}

    def _estimate_price(self, ingredient: str) -> int:
        price_map = {
            "onion": 40, "tomato": 50, "potato": 30, "palak": 40,
            "paneer": 80, "oil": 180, "rice": 60, "chicken": 240,
            "salt": 20, "turmeric": 30, "garam masala": 50
        }
        ingredient_lower = ingredient.lower()
        for key, price in price_map.items():
            if key in ingredient_lower:
                return price
        return 50

    def _calculate_total(self, items: list, people: int) -> dict:
        total = sum(item["price_inr"] for item in items)
        return {
            "items": items,
            "total_inr": total,
            "people": people,
            "agent_version": "CartAgent v1.0"
        }

    def is_greeting(self, text: str) -> bool:
        greetings = ['hi', 'hello', 'hey', 'namaste', 'hii']
        text_lower = text.lower().strip()
        return any(text_lower == g or text_lower.startswith(g + ' ') for g in greetings)
