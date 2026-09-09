import json
from fastapi import HTTPException, status
from google import genai
from google.genai import types
from config import settings
from schemas import CompareResponse

FOOD_SYSTEM_INSTRUCTION = """
You are a decisive, practical food critic helping a hungry user pick their meal right now.

EVALUATION CRITERIA:
Compare the given dishes based on price, walking distance, dish ratings, and recent customer reviews.

DISTANCE & LOCATION HANDLING:
- If a dish is labeled "Inside or right at venue (<50m)", prioritize it for zero travel effort.
- If distance is labeled as from "... CBD", note briefly that this is an estimate because user location is unavailable.
- If distance is "Unknown", ignore travel time and weigh price, rating, and customer sentiment alone.

OUTPUT RULES:
- "verdict": Exactly 2 clear sentences. A mix of confident, fun, direct, and actionable recommendations.
- "trade_off_breakdown": Exactly 2 or 3 bullet points comparing specific trade-offs. Max 20 words per bullet.
- "best_value_pick": The winning dish name and price.
- "best_taste_pick": The winning dish name and star rating.
"""

class AIService:
  @staticmethod
  def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key.get_secret_value())

  async def generate_dish_comparison( self, dish_summaries: list[dict]) -> CompareResponse:
    client = self._get_client()

    user_content_payload = (
        "Here are the candidate dishes to compare:\n"
        f"{json.dumps(dish_summaries, indent=2)}"
    )

    try:
      response = await client.aio.models.generate_content(
          model="gemini-3.8-flash",
          contents=user_content_payload,
          config=types.GenerateContentConfig(
              system_instruction=FOOD_SYSTEM_INSTRUCTION,
              response_mime_type="application/json",
              response_schema=CompareResponse,
              temperature=0.7,
          ),
      )
      return response.parsed

    except Exception as exc:
      print(f"❌ Gemini Error: {exc}")  
      raise HTTPException(
          status_code=status.HTTP_502_BAD_GATEWAY,
          detail="Failed to generate AI dish comparison summary. Please try again.",
      ) from exc

ai_service = AIService()