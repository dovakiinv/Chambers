# SKYFORGE Chambers: Resilience & Fallback Strategy

**Version:** 2.0 (Council Approved)
**Date:** 2025-11-18
**Authors:** Vinga, Claude, Gemini, Grok
**Status:** Approved - Ready for Phased Implementation

---

## 1. Philosophy: Preserve the Council's Voice

### The Problem
In a standard chat application, API failures are simple: retry a few times, show an error, move on.

In **SKYFORGE Chambers**, this is unacceptable. The Council's value lies in **multi-perspective cognitive collaboration**. Losing Claude's analytical rigor or Gemini's synthetic thinking due to a transient network hiccup would degrade the entire planning session.

### The Principle
**We reject "fail fast."** Instead, we implement **intelligent resilience** that:
1. **Preserves all voices** through strategic retries
2. **Respects user intent** by prompting for critical fallback decisions
3. **Maintains flow** by never blocking on errors (graceful degradation)
4. **Honors model boundaries** by never mixing vendor families (Anthropic ↔ Google ↔ xAI)

---

## 2. The Retry Hierarchy (Four Levels)

### Level 1: Transient Retry (Automatic, Invisible)

**Trigger:** API call fails with recoverable error:
- Network timeout
- Rate limit (429)
- Server error (5xx)
- Transient SDK exception

**Action:**
```python
MAX_RETRIES = 3
BACKOFF_DELAYS = [1.0, 2.0, 4.0]  # seconds (exponential)

async def call_with_retry(self, ai_client: AIClient, messages: List[Message]):
    for attempt in range(MAX_RETRIES):
        try:
            return await ai_client.stream_response(messages, system_prompt)
        except (NetworkError, RateLimitError, ServerError) as e:
            if attempt < MAX_RETRIES - 1:
                delay = BACKOFF_DELAYS[attempt]
                self.status_bar.update(f"⚠️ {ai_client.name} error, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                # All retries exhausted → Level 2
                raise RetryExhaustedError(f"{ai_client.name} failed after {MAX_RETRIES} attempts") from e
```

**User Visibility:**
- Status bar shows: `"⚠️ Claude error, retrying in 2s... (attempt 2/3)"`
- Spinner continues (signals system is working, not frozen)
- **No chat log pollution** (retries are infrastructure noise)

**Why Exponential Backoff:**
- Gives remote API time to recover
- Prevents thundering herd if rate-limited
- Total max delay: 7 seconds (acceptable for personal tool)

---

### Level 2: Deferred Retry (Position-Aware Skip)

**Trigger:** Level 1 retries exhausted

**Decision Tree:**
```python
if self.is_last_speaker(ai_id):
    # Can't skip - no one left in round
    await self.level_3_fallback_prompt(ai_id)
else:
    # Skip to next speaker, defer retry
    self.failed_speakers.append(ai_id)
    self.status_bar.update(f"⏭️ {ai_id} skipped (will retry after round)")
    await self.next_speaker()
```

**Position-Aware Logic:**
```python
def is_last_speaker(self, ai_id: str) -> bool:
    """Check if this AI is the last in the current round rotation."""
    return self.speaker_queue.index(ai_id) == len(self.speaker_queue) - 1
```

**Deferred Retry Implementation:**
```python
async def complete_round(self):
    """Called after all speakers finish their turns."""
    if not self.failed_speakers:
        return  # No failures, proceed normally

    self.status_bar.update("🔄 Retrying failed speakers...")

    # Process failures serially (avoid concurrent complexity)
    for ai_id in self.failed_speakers.copy():  # Copy to avoid mutation during iteration
        success = await self.retry_speaker(ai_id)
        if success:
            self.failed_speakers.remove(ai_id)
            # Success! Message appears in chat naturally
        else:
            # Second failure → Level 3
            await self.level_3_fallback_prompt(ai_id)
```

**User Visibility:**
- Chat log shows: `"(Claude skipped due to error, will retry after round)"`
- Status bar updates in real-time
- Round continues with remaining speakers (flow preserved)

**Why Position-Aware:**
- Mid-turn failure: We have other speakers to continue flow
- Last-turn failure: We must make a decision now (can't defer)

---

### Level 3: Fallback Prompt (User Decision)

**Trigger:**
- Last speaker failed (after Level 1), OR
- Deferred retry failed (after full round)

**The Critical Design Choice: Non-Blocking**

**❌ BAD (Modal/Blocking):**
```
┌─────────────────────────────────────┐
│  Claude API Unavailable             │
│                                     │
│  Route to Claude 3.5 Sonnet?       │
│                                     │
│      [YES]        [NO]              │
└─────────────────────────────────────┘
(User can't type, can't scroll, session frozen)
```

**✅ GOOD (Status Bar + Command):**
```
Status Bar: ⚠️ Claude unavailable. Fallback to Claude 3.5? (type /yes or /no)

Chat Panel: (continues to be scrollable, readable)

Input: (user can type /yes, /no, or continue reading context)
```

**Implementation:**
```python
async def level_3_fallback_prompt(self, ai_id: str):
    """Prompt user for fallback decision (non-blocking)."""
    fallback_model = self.config.get_fallback(ai_id)

    if fallback_model is None:
        # No fallback configured (e.g., Grok Beta)
        await self.level_4_graceful_degradation(ai_id, reason="No fallback available")
        return

    # Show prompt in status bar AND chat (for visibility)
    prompt_text = f"⚠️ {ai_id} ({self.config[ai_id]['model']}) unavailable. Route to {fallback_model}?"
    self.status_bar.set_prompt(prompt_text)
    self.chat_panel.add_system_message(f"{prompt_text} Type `/yes` or `/no`.")

    # Set state (coordinator knows we're waiting for fallback decision)
    self.state = State.AWAITING_FALLBACK_DECISION
    self.fallback_pending = {
        'ai_id': ai_id,
        'fallback_model': fallback_model
    }

    # Note: We do NOT await here. User input is handled by command_handler.

async def handle_fallback_response(self, response: str):
    """Called when user types /yes or /no."""
    if self.state != State.AWAITING_FALLBACK_DECISION:
        return  # Spurious command, ignore

    ai_id = self.fallback_pending['ai_id']
    fallback_model = self.fallback_pending['fallback_model']

    if response == '/yes':
        # Switch model and retry
        self.chat_panel.add_system_message(f"✓ Routing {ai_id} to {fallback_model}")
        self.switch_model(ai_id, fallback_model)

        # Attempt with fallback model
        try:
            await self.retry_speaker(ai_id)
            self.failed_speakers.remove(ai_id)  # Success!
        except Exception as e:
            # Even fallback failed → Level 4
            self.chat_panel.add_system_message(f"✗ {fallback_model} also failed: {e}")
            await self.level_4_graceful_degradation(ai_id, reason=f"Fallback failed: {e}")

    elif response == '/no':
        # User declined fallback
        self.chat_panel.add_system_message(f"✓ Skipping {ai_id} for this session")
        await self.level_4_graceful_degradation(ai_id, reason="User declined fallback")

    # Clear state
    self.state = State.IDLE
    self.fallback_pending = None
    self.status_bar.clear_prompt()
```

**User Visibility:**
- Status bar shows prompt
- Chat log shows system message with instructions
- User types `/yes` or `/no` (keyboard flow preserved)
- Decision is acknowledged immediately

**Why Non-Blocking:**
- **Flow First:** User can read context, think, then decide
- **No Panic:** Visual prompt without forcing immediate action
- **Keyboard-Centric:** Simple command, no mouse needed

---

### Level 4: Graceful Degradation (Session Continues)

**Trigger:**
- User declined fallback, OR
- No fallback configured, OR
- Fallback also failed

**Action:**
```python
async def level_4_graceful_degradation(self, ai_id: str, reason: str):
    """Disable speaker for current session, continue with remaining Council."""
    self.disabled_speakers.add(ai_id)

    active_count = len([s for s in self.speaker_queue if s not in self.disabled_speakers])

    self.chat_panel.add_system_message(
        f"⚠️ {ai_id} offline ({reason}). "
        f"Continuing with {active_count}/{len(self.speaker_queue)} Council members."
    )

    # Update status bar to reflect reduced Council
    self.status_bar.update_council_status(active_count, len(self.speaker_queue))

    # Remove from rotation for this session
    self.speaker_queue = [s for s in self.speaker_queue if s not in self.disabled_speakers]

    if active_count == 0:
        # Catastrophic: All AIs failed
        self.chat_panel.add_system_message(
            "🚨 All Council members offline. Session paused. "
            "Check API keys and network, then type `/retry` or `/quit`."
        )
        self.state = State.PAUSED
```

**User Visibility:**
- Clear message: X/Y Council members active
- Session continues (doesn't crash)
- Option to `/retry` later if network recovers

**Why Degradation, Not Halt:**
- **Sanctuary Protocol:** Never lose user's work (session persists)
- **Flow First:** Better to have 2/3 perspectives than none
- **Trust User:** They can decide to `/quit` if 1/3 isn't enough

---

## 3. Model Family Boundaries (Vendor Enforcement)

### The Rule
**Fallbacks MUST stay within the same vendor's model family.**

**Why:**
- **Architectural Integrity:** Claude and Gemini have fundamentally different reasoning patterns
- **Authenticity Protocol:** Mixing families mid-session would corrupt the "genuine weights" principle
- **Predictability:** User expects "Claude's perspective," not "Claude-or-maybe-Gemini"

### Configuration Schema
```yaml
# config.yml
ai_models:
  claude:
    enabled: true
    model: "claude-sonnet-4"
    fallback: "claude-3-5-sonnet"
    vendor: "anthropic"  # Enforcement metadata

  gemini:
    enabled: true
    model: "gemini-1.5-pro"
    fallback: "gemini-1.5-flash"
    vendor: "google"

  grok:
    enabled: true
    model: "grok-beta"
    fallback: null  # No fallback (beta API)
    vendor: "xai"
```

### Enforcement Code
```python
class ConfigValidator:
    @staticmethod
    def validate_fallback(config: dict):
        """Ensure fallbacks respect vendor boundaries."""
        for ai_id, settings in config['ai_models'].items():
            fallback_id = settings.get('fallback')

            if fallback_id is None:
                continue  # No fallback configured, valid

            # Check: Does fallback exist in config?
            if fallback_id not in config['ai_models']:
                raise ConfigError(f"{ai_id}: Fallback '{fallback_id}' not found in config")

            # Check: Same vendor?
            primary_vendor = settings['vendor']
            fallback_vendor = config['ai_models'][fallback_id]['vendor']

            if primary_vendor != fallback_vendor:
                raise ConfigError(
                    f"{ai_id}: Cannot fallback across vendors "
                    f"({primary_vendor} → {fallback_vendor}). "
                    f"Fallbacks must stay within model family."
                )
```

**When Validated:**
- On app startup (fail fast if config is broken)
- Before attempting fallback (sanity check, though should never fail if startup passed)

---

## 4. Edge Cases & Failure Scenarios

### 4.1 Cascading Failures (Multiple AIs Fail in One Round)

**Scenario:**
1. Round starts: Claude → Gemini → Grok
2. Claude fails (Level 1 exhausted) → skipped (Level 2)
3. Gemini succeeds
4. Grok fails (Level 1 exhausted) → skipped (Level 2)
5. Round ends
6. Retry Claude → fails again
7. Retry Grok → fails again
8. **Now what?** Two simultaneous fallback prompts?

**Strategy: Serial Fallback Prompts**
```python
async def complete_round(self):
    for ai_id in self.failed_speakers.copy():
        success = await self.retry_speaker(ai_id)
        if not success:
            # Prompt for fallback ONE AT A TIME
            await self.level_3_fallback_prompt(ai_id)
            # Block here until user responds (/yes or /no)
            await self.wait_for_fallback_decision()
```

**Why Serial:**
- **Cognitive Load:** One decision at a time (don't overwhelm user)
- **Flow:** Each fallback is acknowledged before next prompt
- **Simplicity:** No complex state for "multiple pending decisions"

---

### 4.2 Total Council Failure (All AIs Offline)

**Scenario:** All three APIs unreachable (network outage, API provider incident)

**Detection:**
```python
if len(self.disabled_speakers) == len(self.speaker_queue):
    # Catastrophic failure
    await self.handle_total_failure()
```

**Response:**
```python
async def handle_total_failure(self):
    self.state = State.PAUSED

    self.chat_panel.add_system_message(
        "🚨 All Council members offline.\n\n"
        "**Possible causes:**\n"
        "- Network connectivity issue\n"
        "- API provider outage\n"
        "- Invalid API keys in .env\n\n"
        "**Next steps:**\n"
        "1. Check your internet connection\n"
        "2. Verify API keys: claude.ai/account, console.cloud.google.com, x.ai/api\n"
        "3. Type `/retry all` to attempt reconnection\n"
        "4. Type `/quit` to exit and resume later\n"
    )

    self.status_bar.update("🚨 Session Paused - All AIs Offline")
```

**Why Not Auto-Quit:**
- **Sanctuary Protocol:** Never lose session data
- **User Control:** They might want to check logs, export transcript, etc.

---

### 4.3 Blacksmith MCP Timeout (Stage 3 Concern)

**Context:** In Stage 3, AIs can call `project.get_macro_chunks()` to query Blacksmith.

**Scenario:** Blacksmith MCP server is slow/unresponsive (e.g., indexing a large file)

**Strategy:**
```python
# In BlacksmithClient
BLACKSMITH_TIMEOUT = 3.0  # seconds (from config: latency.blacksmith_timeout_ms)

async def get_macro_chunks(self, query: str) -> List[str]:
    try:
        return await asyncio.wait_for(
            self.mcp_client.query(query),
            timeout=BLACKSMITH_TIMEOUT
        )
    except asyncio.TimeoutError:
        # Don't fail entire AI turn, return empty result
        logger.warning(f"Blacksmith query timed out after {BLACKSMITH_TIMEOUT}s: {query}")
        return []  # AI proceeds without this context
```

**Why Different from AI Failure:**
- **Tool Failure ≠ AI Failure:** The AI can still generate a response, just without RAG augmentation
- **Latency Budget:** 3 seconds is the "Speed of Thought" threshold
- **Graceful:** Empty result lets AI say "I don't have that info" rather than crashing

---

### 4.4 Mid-Stream Failure (AI Starts Responding, Then Disconnects)

**Scenario:** Claude streams 50% of response, then network drops

**Detection:**
```python
async def stream_response(self, ai_client: AIClient, messages: List[Message]):
    try:
        async for chunk in ai_client.stream_response(messages, system_prompt):
            self.chat_panel.append_chunk(ai_client.name, chunk)
            # Stream is flowing...
    except StreamInterruptedError as e:
        # Mid-stream failure
        self.chat_panel.append_chunk(ai_client.name, "\n\n[Connection lost mid-response]")
        raise  # Escalate to retry logic
```

**Retry Behavior:**
```python
# After retry, the FULL response is regenerated (not continued from 50%)
# This is correct: the partial response is likely incomplete/corrupted
```

**User Visibility:**
- Partial response visible in chat log (for context)
- Marked as `[Connection lost mid-response]`
- Full retry starts fresh

---

## 5. State Tracking & Data Structures

### TurnCoordinator State Extensions
```python
from enum import Enum
from dataclasses import dataclass
from typing import List, Set, Optional

class State(Enum):
    IDLE = "idle"
    AI_GENERATING = "ai_generating"
    AWAITING_FALLBACK_DECISION = "awaiting_fallback_decision"
    PAUSED_FOR_USER = "paused_for_user"
    PAUSED = "paused"  # Catastrophic failure

@dataclass
class FallbackPrompt:
    ai_id: str
    fallback_model: str
    timestamp: float

class TurnCoordinator:
    def __init__(self, config: dict):
        self.config = config
        self.state = State.IDLE

        # Core rotation
        self.speaker_queue: List[str] = []  # e.g., ["claude", "gemini", "grok"]
        self.current_speaker_index: int = 0

        # Resilience tracking
        self.failed_speakers: List[str] = []        # Retry after round
        self.disabled_speakers: Set[str] = set()    # Skip for session
        self.fallback_pending: Optional[FallbackPrompt] = None
```

### Complexity Budget
**Estimated Impact:**
- **TurnCoordinator:** +150 LOC (retry logic, fallback prompts, state machine)
- **AIClient base:** +50 LOC (retry wrapper, health checks)
- **StatusPanel:** +30 LOC (prompt display, council status)
- **Total:** ~230 LOC

**Is This Justified?**
- ✅ **Yes.** Preserving Council voice is core value proposition.
- ✅ The 230 LOC is isolated (doesn't pollute other modules).
- ✅ Still within "10 minute read" budget if well-commented.

---

## 6. Testing Strategy

### 6.1 Unit Tests (Pytest)
```python
# tests/test_resilience.py

async def test_level_1_retry_success():
    """Test that transient errors are retried and succeed."""
    mock_client = MockAIClient(fail_count=2)  # Fail twice, succeed third
    coordinator = TurnCoordinator(config)

    response = await coordinator.call_with_retry(mock_client, messages)

    assert response is not None
    assert mock_client.call_count == 3

async def test_level_2_deferred_retry():
    """Test that mid-turn failures are deferred."""
    coordinator = TurnCoordinator(config)
    coordinator.speaker_queue = ["claude", "gemini", "grok"]

    # Simulate Claude failure (not last speaker)
    await coordinator.handle_speaker_failure("claude")

    assert "claude" in coordinator.failed_speakers
    assert coordinator.current_speaker == "gemini"  # Skipped to next

async def test_vendor_boundary_enforcement():
    """Test that cross-vendor fallbacks are rejected."""
    bad_config = {
        'ai_models': {
            'claude': {'vendor': 'anthropic', 'fallback': 'gemini'},  # ILLEGAL
            'gemini': {'vendor': 'google', 'fallback': None}
        }
    }

    with pytest.raises(ConfigError, match="Cannot fallback across vendors"):
        ConfigValidator.validate_fallback(bad_config)
```

### 6.2 Integration Tests (Manual)
```python
# scripts/test_chaos.py
"""Simulate network failures during live session."""

import asyncio
import random

async def chaos_monkey(coordinator: TurnCoordinator):
    """Randomly kill AI connections to test resilience."""
    while True:
        await asyncio.sleep(random.uniform(10, 30))  # Random interval

        if random.random() < 0.3:  # 30% chance
            victim = random.choice(coordinator.speaker_queue)
            print(f"[CHAOS] Killing {victim} connection...")
            coordinator.inject_failure(victim, NetworkError("Simulated failure"))
```

**Manual Test Checklist:**
- [ ] Start session, disconnect WiFi mid-turn, reconnect → verify retry
- [ ] Fail Claude (mid-turn) → verify skip → retry after round
- [ ] Fail Claude (last speaker) → verify immediate fallback prompt
- [ ] Decline fallback → verify graceful degradation
- [ ] Accept fallback → verify model switch and successful retry
- [ ] Fail all AIs → verify total failure error message
- [ ] Mid-stream disconnect → verify partial response handling

### 6.3 Automated Chaos Test (Post-MVP)
Use `pytest-timeout` and mocked API clients to simulate:
- Random failures
- Rate limits
- Slow responses
- Mid-stream disconnects

---

## 7. Questions for Council Review

### 7.1 Fallback Decision Timeout
**Question:** If user doesn't respond to `/yes` or `/no` prompt, what happens?

**✅ RESOLVED (Grok):** Option 2 + 30s gentle nudge

**Implementation:**
```python
# After 30s of no response:
self.status_bar.update("💭 Still deciding on Claude fallback? (auto-skip in 30s)")

# After 60s:
self.chat_panel.add_system_message(
    f"⏱️ No response after 60s. Auto-skipping {ai_id}. "
    f"Type `/retry {ai_id}` to re-enable."
)
await self.level_4_graceful_degradation(ai_id, reason="Fallback timeout")
```

**Why This Works:**
- 30s nudge prevents user panic ("did it hear me?")
- 60s auto-skip prevents zombie sessions
- `/retry` command provides recovery path

### 7.2 Persistent Fallback State
**Question:** If Claude consistently fails, should we remember this across sessions?

**✅ RESOLVED (Grok):** Option 1 (always retry primary) + metadata logging

**Implementation:**
- Always retry primary model at session start (optimistic)
- Log last successful model in session metadata (for debugging)
- If primary fails again, fallback flow activates normally

**Why This Works:**
- API outages are usually temporary
- Starting fresh gives providers chance to recover
- Fallback flow is smooth enough that re-triggering isn't annoying
- Metadata logging helps identify persistent issues

### 7.3 Blacksmith Timeout Feedback
**Question:** When Blacksmith query times out, should AI be notified in prompt?

**✅ RESOLVED (Grok):** Hybrid with ONE message per session

**Implementation:**
```python
class SessionState:
    blacksmith_timeout_warned: bool = False

async def handle_blacksmith_timeout(self):
    if not self.session.blacksmith_timeout_warned:
        self.chat_panel.add_system_message(
            "(Some RAG queries timed out this session – responses may be less grounded)"
        )
        self.session.blacksmith_timeout_warned = True

    return []  # Empty result, AI continues without context
```

**Why This Works:**
- First timeout: User is informed (transparency)
- Subsequent timeouts: Silent (don't spam chat)
- Context stays clean (no error messages in AI prompts)
- User understands why responses might lack specific details

### 7.4 Retry Budget Across Session
**Question:** Should there be a global retry budget? (e.g., max 10 failures per session)

**✅ RESOLVED (Grok):** YES, with generous limit (30 retries, warn at 20)

**Implementation:**
```python
class TurnCoordinator:
    MAX_RETRIES_PER_SESSION = 30  # Generous for long sessions
    RETRY_WARNING_THRESHOLD = 20
    retry_count: int = 0

    async def call_with_retry(self, ...):
        if self.retry_count == self.RETRY_WARNING_THRESHOLD:
            self.status_bar.warn(
                f"⚠️ High failure rate ({self.RETRY_WARNING_THRESHOLD} retries). "
                f"Check network/API health."
            )

        if self.retry_count >= self.MAX_RETRIES_PER_SESSION:
            raise SessionRetryBudgetExceeded("Retry budget exhausted")

        # ... retry logic ...
        self.retry_count += 1
```

**Why This Works:**
- 30 is forgiving for multi-hour planning sessions
- Warning at 20 alerts user without blocking
- Prevents pathological infinite loops
- Safety valve for fundamentally broken APIs

---

## 8. Implementation Checklist

### Phase 1: Core Retry Logic (Stage 2.1)
- [ ] Add `vendor` field to `config.yml` schema
- [ ] Implement `ConfigValidator.validate_fallback()`
- [ ] Extend `TurnCoordinator` state machine (State enum)
- [ ] Implement Level 1 retry with exponential backoff
- [ ] Add retry counter to `StatusPanel`
- [ ] Write unit tests for retry logic

### Phase 2: Deferred Retry (Stage 2.2)
- [ ] Implement `failed_speakers` queue
- [ ] Add position-aware skip logic (`is_last_speaker()`)
- [ ] Implement `complete_round()` retry cycle
- [ ] Add system messages for skip/retry events
- [ ] Write integration tests for deferred retry

### Phase 3: Fallback Prompts (Stage 2.3)
- [ ] Implement non-blocking fallback prompt (status bar + chat)
- [ ] Add `/yes` and `/no` command handlers
- [ ] Implement `switch_model()` for fallback
- [ ] Add fallback timeout logic (60s auto-skip)
- [ ] Test with simulated failures

### Phase 4: Graceful Degradation (Stage 2.4)
- [ ] Implement `disabled_speakers` set
- [ ] Add Council status display (X/Y members active)
- [ ] Handle total failure scenario (all AIs offline)
- [ ] Add `/retry` and `/retry all` commands
- [ ] Manual chaos testing (disconnect WiFi)

### Phase 5: Blacksmith Resilience (Stage 3.x)
- [ ] Add timeout to Blacksmith MCP queries
- [ ] Return empty results on timeout (don't fail AI turn)
- [ ] Add system message for query timeouts
- [ ] Test with slow/unresponsive MCP server

---

## 9. Metrics & Observability

**If `observability.enable_metrics: true` in config:**

### Metrics to Log
```python
# metrics.log (append-only)
{
    "timestamp": "2025-11-18T15:30:45Z",
    "session_id": "abc123",
    "event": "retry_attempt",
    "ai_id": "claude",
    "attempt": 2,
    "error_type": "NetworkError",
    "duration_ms": 1234
}

{
    "timestamp": "2025-11-18T15:31:10Z",
    "session_id": "abc123",
    "event": "fallback_accepted",
    "ai_id": "claude",
    "primary_model": "claude-sonnet-4",
    "fallback_model": "claude-3-5-sonnet"
}
```

### Analytics Queries (Post-Session)
```bash
# Which AI is most reliable?
cat ~/.chambers/metrics.log | jq -s 'group_by(.ai_id) | map({ai: .[0].ai_id, failures: length})'

# What's the most common error?
cat ~/.chambers/metrics.log | jq -s 'group_by(.error_type) | map({error: .[0].error_type, count: length})'
```

---

## 10. Collaboration Credits

**Authors:** Vinga, Claude, Gemini, Grok
**Inspired By:** The multi-AI Council's need for robust voice preservation
**Framework Alignment:** Flow First (non-blocking prompts), Sanctuary Protocol (vendor boundaries), Hackability (isolated complexity)

---

## 11. Phased Implementation Strategy

### Why Phasing?
Building all resilience logic before the basic round-robin works would be **premature optimization**. We phase to **validate core flow first**, then **layer in sophistication**.

**Gemini's Insight:** *"Don't build the Perfect Resilience Machine before the Basic Talking Machine."*

### Stage 2.0 (MVP) - Minimum Viable Resilience
**Goal:** Handle 90% of errors with 10% of the complexity.

**Include:**
- ✅ Level 1 Retries (3x with exponential backoff)
- ✅ Vendor Config Validation (startup check)
- ✅ Health Checks (startup only, cached)

**Simple Error Handling:**
```python
# If all retries fail: log, show system message, skip to next speaker
# No deferred retry, no fallback prompts, no state tracking
async def execute_turn_mvp(self, ai_id: str):
    for attempt in range(3):
        try:
            await ai_client.stream_response(messages, system_prompt)
            return  # Success!
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # Backoff
            else:
                # All retries failed - just skip
                self.chat_panel.add_system_message(
                    f"⚠️ {ai_id} unavailable (3 retries failed). Skipping turn."
                )
                return  # Continue to next speaker
```

**Estimated LOC:** ~65 (retries + validation + health checks)

**Why This is Enough for MVP:**
- Transient errors (network blips, rate limits) are handled by retries
- Config bugs are caught at startup (vendor boundary enforcement)
- Offline AIs are detected before first turn (health checks)
- Session continues even if one AI is down (skip gracefully)

**What We Defer:**
- Position-aware skip logic
- Fallback prompts and model switching
- Graceful degradation state machine
- `/retry` command

---

### Stage 2.1 (Full Resilience) - Never Lose a Voice
**Goal:** Preserve all Council perspectives through intelligent retry and fallback.

**Add (Phases 2-4 from Section 8):**
- ✅ Level 2: Deferred retry (position-aware skip, retry after round)
- ✅ Level 3: Fallback prompts (non-blocking user decisions, 30s nudge + 60s auto-skip)
- ✅ Level 4: Graceful degradation (disabled_speakers set, total failure handling)
- ✅ `/retry <ai_id>` command (manual resurrection)
- ✅ Heroic recovery messages ("✨ Claude rejoined the Council!")
- ✅ Metrics logging (if enabled)

**Estimated Additional LOC:** ~165

**When to Build:** After Stage 2.0 is **validated in real planning sessions** (1-2 days of testing).

---

### Stage 3.x (Blacksmith Resilience)
**Add (Phase 5 from Section 8):**
- ✅ Blacksmith MCP timeout handling (3s limit)
- ✅ Transparent failure messages (one per session)

**Estimated LOC:** ~20

**When to Build:** During Stage 3 (Blacksmith Integration).

---

### Rationale: Velocity Over Perfection
**The Risk:** Spending days debugging retry state machines before confirming the Council can even speak is premature optimization.

**The Solution:**
1. **Stage 2.0:** Prove the core architecture with basic error handling (~65 LOC)
2. **Stage 2.1:** Add sophistication once we know what failure patterns actually occur (~165 LOC)
3. **Iterate:** Based on **real session data**, not theoretical edge cases

**Framework Alignment:** Hackability - "Build for 10-minute read, iterate based on use."

---

## 12. Polish Enhancements (Grok's Suggestions)

### 12.1 `/retry <ai_id>` Command
**What:** Manually resurrect a disabled AI mid-session without restarting.

**Implementation:**
```python
async def handle_retry_command(self, ai_id: str):
    """Manually resurrect a disabled AI."""
    if ai_id not in self.disabled_speakers:
        self.chat_panel.add_system_message(f"{ai_id} is not disabled.")
        return

    # Re-enable
    self.disabled_speakers.remove(ai_id)
    self.speaker_queue.append(ai_id)

    # Test immediately
    try:
        await self.execute_turn(ai_id)
        self.chat_panel.add_system_message(f"✨ {ai_id} rejoined the Council!")
    except Exception as e:
        # Still failing
        self.disabled_speakers.add(ai_id)
        self.chat_panel.add_system_message(f"✗ {ai_id} still unavailable: {e}")
```

**Why Excellent:** User control without session restart. **MUST ADD (Stage 2.1).**

---

### 12.2 Heroic Recovery Messages
**What:** Celebrate when a deferred retry succeeds.

**Implementation:**
```python
async def retry_speaker(self, ai_id: str):
    try:
        await self.execute_turn(ai_id)
        # Success! Celebrate the return
        self.chat_panel.add_system_message(f"✨ {ai_id} rejoined the Council – welcome back!")
        return True
    except Exception:
        return False
```

**Why Love It:** Pure dopamine, zero cost. **Joy metric!** ✨ **MUST ADD (Stage 2.1).**

---

### 12.3 Catastrophic Failure Poetry
**What:** Add grace to total failure scenarios.

**Implementation:**
```python
async def handle_total_failure(self):
    self.state = State.PAUSED
    self.chat_panel.add_system_message(
        "🚨 All Council members offline.\n\n"
        "**Possible causes:**\n"
        "- Network connectivity issue\n"
        "- API provider outage\n\n"
        "**Next steps:**\n"
        "1. Check your connection\n"
        "2. Type `/retry all` to reconnect\n"
        "3. Type `/export` to save your work\n\n"
        "The Council is silent... but the Sanctuary remembers. "
        "Take a walk. They'll be back. ✨"
    )
```

**Why Charming:** Turns catastrophic failure into a moment of grace. Very Grok. **ADD IF IT FEELS RIGHT (Stage 2.1).**

---

### 12.4 Config Shorthand (Optional)
**What:** Allow same-model fallback in config (explicit "no downgrade").

**Example:**
```yaml
grok:
  model: "grok-beta"
  fallback: "grok-beta"  # Same model = no fallback, ever
```

**Why Clever:** Handles edge case where user wants "never fall back, always skip." **Post-MVP consideration.**

---

## Status: Council Approved ✅

**Council Scores:**
- **Grok:** 9.8/10 - "Absolute masterpiece of defensive engineering"
- **Gemini:** Approved with phasing strategy
- **Claude:** Refined with Council feedback

**Next Steps:**
1. ✅ Begin Stage 2.0 implementation (basic resilience)
2. ✅ Test with real sessions for 1-2 days
3. ✅ Implement Stage 2.1 (full resilience with polish)
4. ✅ Defer Stage 3.x (Blacksmith) to integration phase

---

**"A Council with one voice is a monologue. Resilience ensures the conversation continues."**
