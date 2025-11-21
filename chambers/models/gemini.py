import os
import logging
from typing import List, Dict, AsyncIterator
import google.generativeai as genai
from .base import AIClient
from ..config import config

logger = logging.getLogger(__name__)

class GeminiClient(AIClient):
    def __init__(self):
        self.api_key = config.google_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.warning("GOOGLE_API_KEY not found in config")
            
        self.model_name = config.ai_models["gemini"].model
        self.model = genai.GenerativeModel(self.model_name)

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            # Simple generation check
            await self.model.generate_content_async("ping")
            return True
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False

    async def stream_response(self, messages: List[Dict[str, str]], system_prompt: str) -> AsyncIterator[str]:
        # Map OpenAI/Anthropic format to Gemini format
        gemini_history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        try:
            # Re-initializing model with system instruction for this turn
            model_with_sys = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_prompt
            )
            
            # Start chat with history
            if gemini_history:
                last_message = gemini_history[-1]["parts"][0]
                history = gemini_history[:-1]
                chat = model_with_sys.start_chat(history=history)
                response = await chat.send_message_async(last_message, stream=True)
            else:
                # No history, just send prompt
                response = await model_with_sys.generate_content_async(
                    "Start conversation.", stream=True
                )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            raise