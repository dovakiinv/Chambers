import os
import logging
from typing import List, Dict, AsyncIterator
from anthropic import AsyncAnthropic
from .base import AIClient
from ..config import config

logger = logging.getLogger(__name__)

class ClaudeClient(AIClient):
    def __init__(self):
        self.api_key = config.anthropic_api_key
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in config")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = config.ai_models["claude"].model

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            # Cheap call to verify connectivity
            await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            return True
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False

    async def stream_response(self, messages: List[Dict[str, str]], system_prompt: str) -> AsyncIterator[str]:
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Claude stream error: {e}")
            raise