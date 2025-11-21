from abc import ABC, abstractmethod
from typing import List, Dict, AsyncIterator, Optional

class AIClient(ABC):
    """Abstract Base Class for AI Models."""

    @abstractmethod
    async def stream_response(self, messages: List[Dict[str, str]], system_prompt: str) -> AsyncIterator[str]:
        """
        Stream the response token by token.
        
        Args:
            messages: List of message dicts [{'role': 'user', 'content': '...'}, ...]
            system_prompt: The system instruction.
            
        Yields:
            Tokens (chunks) of the response.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify API key and connectivity.
        
        Returns:
            True if healthy, False otherwise.
        """
        pass

    @staticmethod
    def _scrub_log(content: str) -> str:
        """Helper to scrub logs (stub for now)."""
        return "[REDACTED]"