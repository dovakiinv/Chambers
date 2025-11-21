# 🤖 Handoff to Claude

**From:** Gemini (via Vinga's Terminal)
**To:** Claude
**Subject:** Implement Resilience & Recovery Logic

---

## 🏁 Current Status

I have built the **Stage 2 Foundation**.
The following files are live and tested (import-wise):
1.  `chambers/models/*.py`: The AI Client Implementations (Claude, Gemini, Grok).
2.  `chambers/coordinator.py`: The MVP TurnCoordinator (Happy Path only).

## 🎯 Your Mission

Refactor `chambers/coordinator.py` to implement the **Resilience & Fallback Strategy** defined in `Stage2_Council_Plan.md`.

### Specific Requirements:

1.  **Consent-Based Recovery:**
    *   Implement the `failed_speakers` queue.
    *   Implement the `complete_round()` logic that retries failed speakers serially.
    *   Implement the logic to prompt for fallback (User Intervention) if retries fail.
    *   *Note:* For the "Prompt", assume you can call a method `self.ui.prompt_user(msg)` - we will wire this to the TUI later.

2.  **Vendor Enforcement:**
    *   Add the `ConfigValidator` logic to ensure fallbacks stay within vendor families (Anthropic->Anthropic).

3.  **Retry Logic:**
    *   Wrap the `get_client(...).stream_response` call with `tenacity` retries (3 attempts, exponential backoff).

4.  **Rotation Persistence:**
    *   Add the `initialize_rotation_markers` logic to load/save rotation state from the DB.

### Files to Modify:
*   `chambers/coordinator.py` (Heavy refactor)
*   `chambers/config.py` (Add `vendor` field to `AIModelConfig` if needed)

### Reference Docs:
*   `chambers/Stage2_Council_Plan.md` ( The Blueprint)
*   `chambers/Resilience_And_Fallbacks.md` (The Deep Logic)

---

**Gemini's Note:**
I kept `coordinator.py` clean and simple. You have a blank canvas for the state machine. Remember the "Hackability" principle: keep the logic readable!

**Good luck, partner. 🤝**
