import json
import asyncio
from fastapi import HTTPException, status
from google import genai
from google.genai import types, errors
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
    def __init__(self):
        # Build the client once and bake retry behavior into it,
        # instead of hand-rolling backoff logic per call.
        retry_options = types.HttpRetryOptions(
            attempts=2,
            initial_delay=1.0,
            max_delay=4.0,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
        self._client = genai.Client(
            api_key=settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(retry_options=retry_options),
        )

    async def generate_dish_comparison(self, dish_summaries: list[dict]) -> CompareResponse:
        user_content_payload = (
            "Here are the candidate dishes to compare:\n"
            f"{json.dumps(dish_summaries, indent=2)}"
        )

        try:
            # chats.create + send_message is the SDK's forward-compatible
            # pattern (generate_content direct calls are getting deprecated
            # for anything touching AFC in the next major version).
            chat = self._client.aio.chats.create(
                model="gemini-3.8-flash",
                config=types.GenerateContentConfig(
                    system_instruction=FOOD_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=CompareResponse,
                    temperature=0.7,
                ),
            )
            response = await asyncio.wait_for(chat.send_message(user_content_payload), timeout=15)
            return response.parsed
        
        except asyncio.TimeoutError as exc:
          raise HTTPException(
              status_code=status.HTTP_504_GATEWAY_TIMEOUT,
              detail="AI took too long — try again.",
          ) from exc

        except errors.ServerError as exc:
            # Retries already exhausted at this point — Gemini is just overloaded.
            print(f"❌ Gemini overloaded after retries: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Our AI recommender is a bit busy — try again in a few seconds.",
            ) from exc

        except Exception as exc:
            print(f"❌ Gemini Error: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate AI dish comparison summary. Please try again.",
            ) from exc

ai_service = AIService()