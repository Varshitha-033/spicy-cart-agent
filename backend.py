"""
Smart Cart Agent - Concierge Agents Track
Kaggle AI Agents Intensive Vibe Coding Capstone
Agent Skills: Reasoning + Tool Use + Computation + Security
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
    SERP_ENABLED = False

class CartAgent:
    def __init__(self):
        self.llm = Groq(api_key=GROQ_KEY)
        self.search_endpoint = "https://serpapi.com/search"
        self.serp_enabled = SERP_ENABLED

    def generate_shopping_list(self, dish: str, people: int) -> dict:
        """
        AGENT SKILL: Multi-step Reasoning + Tool Use + Computation
        FIX: Always get base for 1 person, then scale by people count
        """
        dish = self._sanitize_input(dish)
        people = max(1, min(people, 20))

        # Step 1: Always get ingredients for 1 PERSON only
        base_ingredients = self._reason_ingredients(dish, 1)

        # Step 2: Get prices for 1 person base
        base_priced_items = self._use_search_tool(base_ingredients)

        # Step 3: Scale quantities and prices by people count
        scaled_items = self._scale_for_people(base_priced_items, people)

        return self._calculate_total(scaled_items, people)

    def _sanitize_input(self, dish: str) -> str:
        """SECURITY: Input sanitization against prompt injection"""
        dish = dish.strip()[:100]
        dish = re.sub(r'[<>{}[\]\\]', '', dish)
        return dish

    def _reason_ingredients(self, dish: str, people: int) -> list:
        """
        AGENT SKILL: Reasoning
        Always generates for 1 PERSON base - we scale later
        """
        prompt = f"""You are a Smart Cart Agent for Indian grocery planning.

Task: List ingredients for "{dish}" for EXACTLY 1 PERSON - single serving only.

CRITICAL RULES:
1. Use MINIMAL realistic quantities for ONE meal only
2. Format: "ingredient - quantity unit" per line only
3. No explanations, just the list
4. Think hostel-style single serving

Example for "palak paneer for 1":
palak - 100g
paneer - 75g
onion - 1 small
tomato - 1 small
ginger-garlic paste - 1 tsp
oil - 1 tbsp
cumin seeds - 1/4 tsp
garam masala - 1/4 tsp
turmeric - pinch
salt - to taste
cream - 1 tsp

Now list ingredients for "{dish}" for 1 person:"""

        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            raw_list = response.choices[0].message.content.strip()
            return [line.strip() for line in raw_list.split('\n') if line.strip() and '-' in line]
        except Exception as e:
            return [f"Error: {str(e)}"]

    def _use_search_tool(self, ingredients: list) -> list:
        """AGENT SKILL: Tool Use - Get base prices for 1 person"""
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
                    price_data = {"price": self._estimate_price(ingredient), "source": "Estimated"}

                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "base_price_inr": price_data["price"], # Base price for 1 person
                    "source": price_data["source"]
                })
            except:
                priced_items.append({
                    "item": ingredient,
                    "quantity": quantity,
                    "base_price_inr": 10,
                    "source": "Estimated"
                })
        return priced_items

    def _scale_for_people(self, base_items: list, people: int) -> list:
        """
        AGENT SKILL: Computation
        Scale quantities and prices linearly by people count
        """
        if people == 1:
            return [{"item": i["item"], "quantity": i["quantity"],
                    "price_inr": i["base_price_inr"], "source": i["source"]}
                   for i in base_items]

        scaled = []
        for item in base_items:
            scaled_qty = self._scale_quantity(item["quantity"], people)
            scaled_price = item["base_price_inr"] * people

            scaled.append({
                "item": item["item"],
                "quantity": scaled_qty,
                "price_inr": scaled_price,
                "source": item["source"]
            })
        return scaled

    def _scale_quantity(self, qty_str: str, multiplier: int) -> str:
        """Smart quantity scaling: 100g * 3 = 300g, 1 small * 3 = 3 small"""
        try:
            # Case 1: "100g", "1 tbsp", "75ml"
            match = re.match(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$', qty_str.strip())
            if match:
                num = float(match.group(1))
                unit = match.group(2)
                scaled_num = num * multiplier
                # Integer chey if whole number
                if scaled_num == int(scaled_num):
                    return f"{int(scaled_num)}{unit}"
                return f"{scaled_num:.1f}{unit}"

            # Case 2: "1 small", "2 medium"
            match = re.match(r'^(\d+)\s+(small|medium|large|tsp|tbsp|pinch)$', qty_str.strip(), re.IGNORECASE)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                return f"{num * multiplier} {unit}"

            # Case 3: "to taste", "pinch" - don't scale
            if qty_str.lower() in ['to taste', 'pinch', 'as needed']:
                return qty_str

            # Default: add x multiplier
            return f"{qty_str} x{multiplier}"
        except:
            return f"{qty_str} x{multiplier}"

    def _fetch_price_from_web(self, ingredient: str) -> dict:
        """Tool: SerpAPI - Real-time price from Blinkit/Zepto"""
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
        """
        AGENT SKILL: Heuristic Reasoning
        Base prices for 1 person single serving - Blinkit 2026 rates
        """
        price_map = {
            "onion": 8, "tomato": 10, "potato": 6, "palak": 10,
            "coriander": 5, "green chili": 3, "ginger": 5, "garlic": 5, "lemon": 3,
            "paneer": 35, "milk": 28, "curd": 15, "butter": 15, "cream": 12, "cheese": 25,
            "chicken": 65, "mutton": 180, "egg": 6, "fish": 80,
            "oil": 25, "rice": 15, "atta": 12, "sugar": 10, "salt": 5, "dal": 20, "tur dal": 25,
            "turmeric": 5, "cumin": 8, "garam masala": 10, "chili powder": 5,
            "coriander powder": 5, "ginger-garlic paste": 8,
            "ghee": 50, "bread": 25, "bun": 15, "patty": 40
        }

        ingredient_lower = ingredient.lower()
        for key, price in price_map.items():
            if key in ingredient_lower:
                return price
        return 10

    def _calculate_total(self, items: list, people: int) -> dict:
        """AGENT SKILL: Computation"""
        total = sum(item["price_inr"] for item in items)
        return {
            "items": items,
            "total_inr": total,
            "people": people,
            "agent_version": "CartAgent v1.1"
        }

    def is_greeting(self, text: str) -> bool:
        greetings = ['hi', 'hello', 'hey', 'namaste', 'hii']
        text_lower = text.lower().strip()
        return any(text_lower == g or text_lower.startswith(g + ' ') for g in greetings)
