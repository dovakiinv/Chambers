"""
SKYFORGE Chambers - Turn Coordinator (Stage 2.0 MVP)

This module implements the basic round-robin turn management with
simple resilience (retry logic, health checks, vendor validation).

Stage 2.1 additions (deferred retry, fallback prompts, etc.) will come later.
"""

import asyncio
import logging
from typing import List, Dict, Optional, Set
from enum import Enum
from collections import deque

from .config import config
from .models.base import AIClient
from .models.claude import ClaudeClient
from .models.gemini import GeminiClient
from .models.grok import GrokClient

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BACKOFF_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff in seconds


class State(Enum):
    """Coordinator states."""
    IDLE = "idle"
    AI_GENERATING = "ai_generating"
    PAUSED_FOR_USER = "paused_for_user"


class ConfigError(Exception):
    """Raised when configuration is invalid."""
    pass


class ConfigValidator:
    """Validates configuration for vendor boundaries and other constraints."""

    @staticmethod
    def validate_vendor_boundaries(ai_models: Dict) -> None:
        """
        Ensure fallback models stay within the same vendor family.

        Raises:
            ConfigError: If a fallback crosses vendor boundaries.
        """
        for ai_id, settings in ai_models.items():
            fallback_id = settings.fallback

            if fallback_id is None:
                continue  # No fallback configured, valid

            # Check: Does fallback model exist in config?
            if fallback_id not in ai_models:
                raise ConfigError(
                    f"{ai_id}: Fallback model '{fallback_id}' not found in config"
                )

            # Check: Same vendor?
            primary_vendor = settings.vendor
            fallback_vendor = ai_models[fallback_id].vendor

            if primary_vendor != fallback_vendor:
                raise ConfigError(
                    f"{ai_id}: Cannot fallback across vendors "
                    f"({primary_vendor} → {fallback_vendor}). "
                    f"Fallbacks must stay within model family (Authenticity Protocol)."
                )

    @staticmethod
    def validate_all() -> None:
        """Run all validation checks on startup."""
        ConfigValidator.validate_vendor_boundaries(config.ai_models)
        logger.info("✓ Config validation passed (vendor boundaries enforced)")


class TurnCoordinator:
    """
    Manages round-robin turn-taking between multiple AI models.

    Stage 2.0 MVP: Basic resilience only.
    - Retry logic (3x + backoff)
    - Health checks (startup)
    - Simple skip on failure

    Stage 2.1 additions (deferred):
    - Position-aware skip
    - Deferred retry
    - Fallback prompts
    - Graceful degradation
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = State.IDLE

        # AI client registry
        self.clients: Dict[str, AIClient] = {}
        self.speaker_queue: deque = deque()

        # Health tracking (checked at startup, cached for session)
        self.healthy_speakers: Set[str] = set()
        self.unhealthy_speakers: Set[str] = set()

    async def initialize(self) -> None:
        """
        Initialize the coordinator:
        1. Validate config
        2. Instantiate AI clients
        3. Run health checks
        4. Build speaker queue
        """
        # Step 1: Validate config
        ConfigValidator.validate_all()

        # Step 2: Instantiate clients for enabled models
        for ai_id, settings in config.ai_models.items():
            if not settings.enabled:
                logger.info(f"Skipping {ai_id} (disabled in config)")
                continue

            # Create client instance
            if ai_id == "claude":
                self.clients[ai_id] = ClaudeClient()
            elif ai_id == "gemini":
                self.clients[ai_id] = GeminiClient()
            elif ai_id == "grok":
                self.clients[ai_id] = GrokClient()
            else:
                logger.warning(f"Unknown AI model: {ai_id}")

        # Step 3: Health checks (startup only, cached for session)
        logger.info("Starting health checks...")
        await self._run_health_checks()
        logger.info(f"Health checks complete. Healthy: {self.healthy_speakers}")

        # Step 4: Build speaker queue from healthy AIs
        self.speaker_queue = deque(self.healthy_speakers)

        if not self.speaker_queue:
            logger.error("CRITICAL: No healthy speakers found!")
            raise RuntimeError(
                "No healthy AI models available. Check API keys and network connectivity."
            )

        logger.info(f"Council initialized: {list(self.speaker_queue)} ({len(self.speaker_queue)} members)")

    async def _run_health_checks(self) -> None:
        """
        Run health checks on all clients (startup only).
        Results are cached for the session.
        """
        logger.info("Running health checks...")

        for ai_id, client in self.clients.items():
            try:
                is_healthy = await client.health_check()
                if is_healthy:
                    self.healthy_speakers.add(ai_id)
                    logger.info(f"  ✓ {ai_id} is healthy")
                else:
                    self.unhealthy_speakers.add(ai_id)
                    logger.warning(f"  ✗ {ai_id} health check failed")
            except Exception as e:
                self.unhealthy_speakers.add(ai_id)
                logger.error(f"  ✗ {ai_id} health check error: {e}")

    async def get_next_speaker(self) -> Optional[str]:
        """
        Get the next speaker in the round-robin rotation.

        Returns:
            AI ID, or None if queue is empty.
        """
        if not self.speaker_queue:
            return None

        # Rotate: move first speaker to back of queue
        self.speaker_queue.rotate(-1)
        return self.speaker_queue[0]

    async def execute_turn(
        self,
        ai_id: str,
        messages: List[Dict[str, str]],
        system_prompt: str,
        stream_callback=None
    ) -> Optional[str]:
        """
        Execute a single AI turn with retry logic (Stage 2.0 MVP).

        Args:
            ai_id: Which AI to use
            messages: Conversation history
            system_prompt: System instruction
            stream_callback: Async function(text: str) -> None

        Returns:
            Full response text, or None if all retries failed
        """
        client = self.clients.get(ai_id)
        if not client:
            logger.error(f"{ai_id} client not found")
            return None

        self.state = State.AI_GENERATING

        # Retry loop (Level 1 resilience)
        for attempt in range(MAX_RETRIES):
            try:
                # Stream the response
                response_chunks = []
                async for chunk in client.stream_response(messages, system_prompt):
                    response_chunks.append(chunk)
                    if stream_callback:
                        await stream_callback(chunk)

                # Success!
                full_response = "".join(response_chunks)
                self.state = State.IDLE
                return full_response

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    # Retry with backoff
                    delay = BACKOFF_DELAYS[attempt]
                    logger.warning(
                        f"{ai_id} error (attempt {attempt + 1}/{MAX_RETRIES}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    logger.error(
                        f"{ai_id} failed after {MAX_RETRIES} attempts: {e}"
                    )
                    self.state = State.IDLE
                    return None

        return None  # Should never reach here, but for safety

    async def run_round(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "You are a helpful AI assistant.",
        stream_callback=None
    ) -> List[Dict[str, str]]:
        """
        Execute one full round of the Council.
        
        Stage 2.1: Supports @Mentions to target specific speakers.
        Default: All speakers (Round Robin).
        """
        responses = []
        
        # 1. Determine Target Speakers
        # Check the last user message for @mentions
        last_user_msg = messages[-1]["content"].lower() if messages else ""
        target_speakers = []
        
        # Check for explicit @Council override (All speak)
        if "@council" in last_user_msg:
            # Use the current queue order (rotation happens below if we used get_next, 
            # but here we just grab the list)
            target_speakers = list(self.speaker_queue)
        else:
            # Check for specific mentions
            found_mentions = []
            # iterating over healthy speakers to find mentions
            for ai_id in self.speaker_queue:
                if f"@{ai_id}" in last_user_msg:
                    found_mentions.append(ai_id)
            
            if found_mentions:
                target_speakers = found_mentions
            else:
                # Default: All Speak (Round Robin sequence)
                # To maintain the rotation effect, we rotate the queue once per round?
                # Or just iterate the current order. 
                # For MVP behavior (everyone speaks), we just list them.
                target_speakers = list(self.speaker_queue)
                # Optional: Rotate the main queue so next time the order changes?
                # self.speaker_queue.rotate(-1) 

        logger.info(f"Target Speakers for this round: {target_speakers}")

        for speaker_id in target_speakers:
            # We do not use get_next_speaker() here because we have a specific list.
            
            logger.info(f"Turn: {speaker_id}")
            
            # Wrap callback to include speaker ID context
            async def scoped_callback(chunk: str):
                if stream_callback:
                    await stream_callback(speaker_id, chunk)

            # Identity Injection in System Prompt
            identity_prompt = (
                f"{system_prompt}\n\n"
                f"You are {speaker_id.upper()}. You are a member of the Skyforge Council. "
                f"Speak ONLY as {speaker_id.upper()}. Do NOT generate text for other speakers. "
                f"Stop speaking immediately after your contribution."
            )

            # Subjective History Transformation (Claude's Fix)
            # Transform history so current speaker sees others as 'user' and self as 'assistant'
            subjective_messages = []
            for msg in messages:
                content = msg["content"]
                role = msg["role"]
                
                if role == "user":
                    # Vinga is always User
                    subjective_messages.append(msg)
                elif role == "assistant":
                    # Check if this is ME speaking
                    # We check specific identity tag format: [Speaker]: ...
                    my_tag = f"[{speaker_id.capitalize()}]:"
                    
                    if content.strip().startswith(my_tag):
                        # It's me -> Assistant (Internal Memory)
                        subjective_messages.append({"role": "assistant", "content": content})
                    else:
                        # It's someone else -> User (External Input)
                        subjective_messages.append({"role": "user", "content": content})

            # Execute turn with retry logic
            response_text = await self.execute_turn(
                speaker_id, 
                subjective_messages, 
                identity_prompt, 
                stream_callback=scoped_callback
            )

            if response_text:
                responses.append({
                    "speaker": speaker_id,
                    "content": response_text,
                    "success": True
                })
                # Add AI response to message history for next speaker (or for next round)
                # Even if other AIs didn't speak, they will see this in the history next time they are called.
                identity_content = f"[{speaker_id.capitalize()}]: {response_text}"
                messages.append({"role": "assistant", "content": identity_content})
            else:
                # All retries failed
                logger.warning(f"Skipping {speaker_id} (unavailable)")
                responses.append({
                    "speaker": speaker_id,
                    "content": f"⚠️ {speaker_id} unavailable (3 retries failed). Skipping turn.",
                    "success": False
                })

        self.state = State.PAUSED_FOR_USER
        return responses
