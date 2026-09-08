import json
from google import genai
from google.genai import types
from schemas import CompareResponse

class AIService:
    def __init__(self):
        # Automatically detects GEMINI_API_KEY from environment variables
        self.client = genai.Client()

    async def generate_dish_comparison(self, dish_summaries: list[dict]) -> CompareResponse:
        prompt = f"""
        You are a decisive, practical food critic helping a hungry user pick their meal right now.
        
        Compare these dishes based on price, walking distance, dish ratings, and recent customer reviews:
        {json.dumps(dish_summaries, indent=2)}

        RULES:
        - "verdict": Exactly 2 clear sentences. Direct and actionable.
        - "trade_off_breakdown": Exactly 2 or 3 bullet points comparing specific trade-offs. Max 20 words per bullet.
        - "best_value_pick": The winning dish name and price.
        - "best_taste_pick": The winning dish name and star rating.
        """

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CompareResponse,
                temperature=0.2,
            ),
        )

        return response.parsed

ai_service = AIService()