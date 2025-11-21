# Stage 2: The Council - Implementation Plan

**Version:** 2.0 (Council Approved)
**Date:** 2025-11-18
**Authors:** Vinga, Claude, Gemini, Grok
**Status:** Ready for Implementation

**Goal:** Transform the single-user skeleton into a multi-AI collaboration engine with round-robin turn management and async user input.

---

## 1. Architectural Components

### 1.1 The `AIClient` Interface (The Universal Translator)
We need a unified way to talk to any model.
```python
class AIClient(ABC):
    async def stream_response(self, messages: List[Message], system_prompt: str) -> AsyncIterator[str]:
        """Stream the response token by token."""
        pass

    async def health_check(self) -> bool:
        """Verify API key and connectivity. Called ONCE at app startup, result cached for session."""
        pass
```
*   **Implementations:** `ClaudeClient`, `GeminiClient`, `GrokClient`.
*   **Resilience:** Each client handles its own retries (Tenacity) and maps native exceptions to a shared `AIError`.
*   **Security Note:** Implementations must **NEVER** log full message content or API keys at INFO level. Debug logs only, and ideally scrubbed.

### 1.2 The `TurnCoordinator` (The Conductor)
This class manages the flow of conversation. It is a State Machine.

**Implementation Note:** Keep it simple. Use standard Python `if/elif` logic or `match` statements. Do NOT import a state machine library.

**States:**
*   `IDLE`: Waiting for input.
*   `AI_GENERATING`: An AI is currently streaming.
*   `PAUSED_FOR_USER`: The round is complete; waiting for Vinga.

**The Rotation Logic:**
*   A `deque` (double-ended queue) of active `AIClient` IDs.
*   `next_turn()` rotates the deque.
*   **Phases:** The `system_prompt` changes based on the active `/phase` (Plan, Critique, etc.).

**Rotation Markers:**
*   On session creation, assign 🎯 (Initial Drafter) and ✅ (Final Writer) based on last session's rotation.
*   **Persistence:** Store in `sessions` table (`rotation_state` column).
*   **Round-Robin Rule:** Rotate marker assignments across sessions for fairness (e.g., if Claude started last time, Gemini starts this time).

### 1.3 The `AsyncQueue` (The Flow Preserver)
Vinga must be able to type *while* Claude is thinking.
*   **Mechanism:** A `asyncio.Queue` for user messages.
*   **Behavior:**
    *   If `State == IDLE`: Process message immediately.
    *   If `State == AI_GENERATING`: Push message to Queue. Update UI "Queued Messages: 1".
    *   **Visual Feedback:** Show immediately in chat as `(Queued) Vinga: ...` with **dimmed styling** to indicate pending state.
    *   **On Turn End:** Coordinator checks Queue. If not empty, injects queued messages into the context *before* the next AI starts.

---

## 2. Implementation Steps

### Step 1: The Client Abstraction
*   Define `chambers/models/base.py` (ABC).
*   Implement `chambers/models/claude.py` (Anthropic).
*   Implement `chambers/models/gemini.py` (Google GenAI).
*   Implement `chambers/models/grok.py` (xAI - using `openai` client with base_url).
*   *Test:* A script `test_models.py` that pings all three.

### Step 2: The Coordinator Core
*   Create `chambers/coordinator.py`.
*   Implement the `TurnCoordinator` class.
*   Implement `RoundRobin` logic with Config-based model loading (respecting `priority` field).
*   *Test:* Unit tests for state transitions and rotation.

### Step 3: TUI Integration (The "Live" Wiring)
*   Update `app.py` to use `TurnCoordinator`.
*   **Chat Widget:** Stick with `RichLog` for Stage 2 MVP. Use `[dim]` tags for queued messages.
    *   *Refactor Note:* If `RichLog` proves too rigid for message updates (undimming), refactor to custom `ChatPanel` in Stage 5.
*   **Mermaid Support:** Implement Mermaid-to-ASCII detection by pre-processing text before sending to `RichLog`.
*   Implement the `Input` handler to feed the `AsyncQueue`.
*   Add `StatusPanel` widget with:
    *   Current speaker indicator (e.g., "Generating... Claude 🤔")
    *   Rotation markers (🎯 Initial, ✅ Final)
    *   Queued message counter (if AsyncQueue not empty)

### Step 4: The Commands
*   Implement `/phase` toggle in `TurnCoordinator`.
*   Implement `/bye` (basic version).

---

## 3. Key Decisions & Tradeoffs

### 3.1 Streaming vs. Block
*   **Decision:** Streaming is mandatory.
*   **Why:** Latency masking. Vinga needs to see thoughts forming.

### 3.2 Error Handling
*   **Strategy:** Multi-level resilience (see `Resilience_And_Fallbacks.md` for complete specification).

**Stage 2.0 (MVP):** Basic resilience (~65 LOC)
1.  **Transient Retry:** 3 attempts with exponential backoff (1s, 2s, 4s)
2.  **Vendor Validation:** Config check at startup (prevent cross-vendor fallbacks)
3.  **Health Checks:** Startup-only API connectivity tests (cached for session)
4.  **Simple Skip:** If all retries fail, skip to next speaker with system message

**Stage 2.1 (Full Resilience):** Advanced recovery (~165 additional LOC)
1.  **Position-Aware Skip:** Mid-turn failures skip, end-turn failures prompt immediately
2.  **Deferred Retry:** Retry skipped speakers after full round completes
3.  **Non-Blocking Fallback Prompts:** Status bar shows `⚠️ Claude unavailable. Fallback to Claude 3.5? (/yes | /no)`
    *   30s gentle nudge: "💭 Still deciding?"
    *   60s auto-skip if no response
4.  **Graceful Degradation:** `disabled_speakers` set, `/retry <ai_id>` command
5.  **Heroic Recovery:** "✨ Claude rejoined the Council!" messages

*   **Why:** "Authenticity First" - Never silently downgrade. "Flow First" - Non-blocking prompts preserve keyboard flow.
*   **Reference:** Full specification in `Resilience_And_Fallbacks.md`

### 3.3 The "Context Payload"
*   **Strategy:** **Hybrid Context (Stage 2 MVP)**.
    *   **Pinned Docs:** Load `auto_load` files from config (e.g., `plan.md`) at session start.
    *   **Recent History:** Last 20 messages from SQLite.
    *   **Total Cap:** ~30k tokens (rough estimate).
*   **Why:** "Flow First." Prevents overflow before Stage 4 (Budgeting) while ensuring critical docs are present.

---

## 4. Questions for the Council (Reviewers)

1.  **Grok's API:** ✅ **RESOLVED** - Use OpenAI compatibility layer (`openai.AsyncOpenAI` with `base_url="https://api.x.ai/v1"`). xAI SDK is unstable as of Nov 2024.
2.  **The "Interruption" UX:** ✅ **RESOLVED** - Show immediately as `(Queued) Vinga: ...` with dimmed/grayed styling to indicate pending state.
