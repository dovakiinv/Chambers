import os
import logging
from typing import List, Dict, AsyncIterator
from openai import AsyncOpenAI
from .base import AIClient
from ..config import config

logger = logging.getLogger(__name__)

class GrokClient(AIClient):
    def __init__(self):
        self.api_key = config.xai_api_key
        if not self.api_key:
            logger.warning("XAI_API_KEY not found in config")
            
        self.client = AsyncOpenAI(
            api_key=self.api_key or "dummy-key-for-init", # Prevent crash on init, fail on health check
            base_url="https://api.x.ai/v1"
        )
        self.model = config.ai_models["grok"].model

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"Grok health check failed: {e}")
            return False

    async def stream_response(self, messages: List[Dict[str, str]], system_prompt: str) -> AsyncIterator[str]:
        try:
            # Prepend system prompt to messages for OpenAI format
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                stream=True,
                temperature=0.7
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            logger.error(f"Grok stream error: {e}")
            raise
