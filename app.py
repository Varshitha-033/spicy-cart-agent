def _reason_ingredients(self, dish: str, people: int) -> list:
        """
        AGENT SKILL: Reasoning
        Uses LLM to decompose dish into ingredient list with MINIMAL quantities for cost control
        """
        # For 1 person, ask for smallest realistic portions
        if people == 1:
            portion_note = "Use MINIMAL quantities - single meal portions only. Example: oil 1 tbsp not 100ml, onion 1 small not 250g"
        else:
            portion_note = f"Realistic quantities for {people} people"

        prompt = f"""You are a Smart Cart Agent for Indian grocery planning.

Task: List ingredients for "{dish}" to serve {people} people.

CRITICAL RULES:
1. {portion_note}
2. Include ALL ingredients - spices, oil, salt everything
3. Format: "ingredient - quantity unit" per line only
4. No explanations, just the list
5. For 1 person: Think single serving, hostel-style portions

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

Now list ingredients for "{dish}" for {people} people:"""

        try:
            response = self.llm.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, # Lower = more precise
                max_tokens=800
            )
            raw_list = response.choices[0].message.content.strip()
            return [line.strip() for line in raw_list.split('\n') if line.strip() and '-' in line]
        except Exception as e:
            return [f"Error: {str(e)}"]
