class CartCompilerAgent:
    """Agent 3: Compiles final table with cheapest links"""
    def __init__(self, client):
        self.client = client
        self.role = """You are CartCompilerAgent. MANDATORY OUTPUT FORMAT:
1. Markdown table: Item | Quantity | Best Price (INR) | Platform
2. Total row at end
3. After table, EXACTLY this line: [CART_DATA]Item1:Qty1:Price1:Platform1:URL1,Item2:Qty2:Price2:Platform2:URL2
4. RULE: Every item MUST have all 5 parts separated by colons. URL is mandatory.
5. NEVER skip URL. Example: Cotton Kurti:1 unit:180:Meesho:https://www.meesho.com/search?q=Cotton+Kurti
6. If URL missing, you FAILED the task."""
    
    def run(self, items_with_prices):
        # Manually construct CART_DATA to guarantee URL
        cart_data_parts = []
        for i in items_with_prices:
            part = f"{i['name']}:{i['qty']}:{i['price']}:{i['platform']}:{i['url']}"
            cart_data_parts.append(part)
        cart_data_string = ",".join(cart_data_parts)
        
        # Ask LLM only for table, we add CART_DATA ourselves
        items_for_table = "\n".join([f"{i['name']} | {i['qty']} | ₹{i['price']} | {i['platform']}" for i in items_with_prices])
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You create markdown tables. Output ONLY the table with Total row. No extra text."},
                {"role": "user", "content": f"Create table with headers Item|Quantity|Best Price (INR)|Platform for:\n{items_for_table}"}
            ],
            model="llama-3.1-8b-instant", temperature=0.3,
        )
        table = response.choices[0].message.content
        return f"{table}\n\n[CART_DATA]{cart_data_string}"
