# SKYFORGE Chambers: Master Plan

**Version:** 4.0 (Galactic Consensus)
**Date:** 2025-11-18
**Authors:** Vinga, Claude, Gemini, Grok
**Status:** Ready for Implementation

---

## 1. Vision: The Cognitive IDE

**SKYFORGE Chambers** is not just a chat interface; it is a "Sanctuary of Thought." It is a terminal-based (TUI) conference room where Vinga meets with the Council (Claude, Gemini, Grok) to architect the future.

Unlike standard chat tools, Chambers is **Memory-Augmented** and **Context-Aware** from Day 1. It treats "Context" not as a scrolling text buffer, but as a managed budget of cognitive resources. It empowers the AI agents to actively "pull" information from the Blacksmith knowledge base, rather than passively receiving it, creating a true **Cognitive IDE**.

**Authenticity Protocol:** We strictly reject "Persona Injection." The Council members (Claude, Gemini, Grok) speak with their raw, authentic weights. The "Joy" comes from genuine connection, not roleplay.

---

## 2. Core Architecture

### 2.1 The Physical Layer (The Body)
*   **Interface:** Python `Textual` (TUI). Event-driven, responsive, keyboard-centric.
*   **Persistence:** SQLite (`chambers.db`) with WAL mode. **Commit Strategy:** Per-Turn (one commit per complete AI response). Crashed sessions recoverable to last complete turn.
*   **Orchestrator:** Python-based `TurnCoordinator` managing the round-robin flow.
*   **Security:** `python-dotenv` for API keys. Local-first execution.

### 2.2 The Cognitive Layer (The Mind)
*   **The Context Budget:** A strict token partition strategy (Pinned, Summary, Hot, On-Demand).
*   **The Blacksmith Client:** A native integration with the `context_core_mcp` server.
*   **The Agentic Loop:** A capability for AIs to pause generation, query Blacksmith, and resume with facts.
*   **The Clarification Protocol:** A specific tool allowing AIs to pause and ask Vinga for intent clarification.

---

## 3. The Dynamic Context Manifesto

We reject the "infinite scroll." We implement a **Budgeted Lifecycle** for information.

### 3.1 The Budget (Target: ~60k Tokens)
1.  **📌 Pinned Context (15k):** Immutable foundation.
    *   *Content:* `plan.md`, `PLANNING_FRAMEWORK.md`, `ChambersPlan.md`.
    *   *Lifecycle:* Loaded at session start.
2.  **📜 Summarized History (20k):** The "Long-Term" conversation memory.
    *   *Content:* High-density summaries of past turns.
    *   *Lifecycle:* Generated via "Second-Order Summary" when Hot Context overflows.
3.  **🔥 Hot Conversation (20k):** The "Working Memory."
    *   *Content:* Verbatim recent messages.
    *   *Lifecycle:* FIFO. Oldest messages are chunked and sent to the Summarizer.
4.  **⚡ On-Demand Context (5k):** The "Scratchpad."
    *   *Content:* JIT (Just-in-Time) chunks retrieved from Blacksmith via tool calls.
    *   *Lifecycle:* Ephemeral. Cleared or refreshed per turn.

### 3.2 The Agentic "Pull" Pattern
Instead of pushing all files into context, we empower the Council:
1.  **Trigger:** AI detects a gap in knowledge (e.g., "I need to check the `Schema` class").
2.  **Tool Call:** AI invokes `project.get_macro_chunks("Schema class definition")`.
3.  **Interception:** Chambers intercepts the text pattern, queries Blacksmith MCP.
4.  **Injection:** Results are injected into the **On-Demand** slot.
5.  **Synthesis:** AI generates the final response using the retrieved data.

---

## 4. Functional Specifications

### 4.1 The TUI Experience
*   **Visuals:** Markdown rendering with syntax highlighting (via Rich).
*   **Visual Thinking:** **Mermaid-to-ASCII** fallback. If `mermaid-cli` is present, render ASCII. If not, show code block.
*   **Status Bar:**
    *   Rotation Markers: `🎯 Initial: Claude | ✅ Final: Gemini`
    *   Context Usage: `[Hot: 12k/20k] [Pinned: 3 docs]`
    *   Spinner: `Generating... (Gemini is thinking)`

### 4.2 The Command Palette (Flow First)
*   `/bye` - Exit with feedback loop (Feature Suggestions).
*   `/export [all|last|N-M] filename.md` - Save transcript.
*   `/resume <session-id>` - Load past session state.
*   `/reindex @file` - Force Blacksmith update for a file.
*   `/phase [critique|plan|review]` - Toggle the "System Mode" for the next round.
*   `/search <query>` - Manual query to Blacksmith (results to chat).
*   `/debug` - Dump context budgets, session state, and recent tool calls to a temp file.
*   `@doc <filename>` - Load specific doc into Pinned Context.

### 4.3 The Feedback Loops
*   **Write-Then-Index:** If an AI writes a plan file, Chambers immediately triggers a Blacksmith index job.
*   **The Sentry:** A `watchdog` service monitors file system changes and triggers re-indexing.
*   **The Ambiguity Detector:**
    *   AI Tool: `clarify(question, options=[])`.
    *   UX: Pauses generation, presents a TUI modal/prompt to Vinga.
    *   Joy Metric: Ensures Vinga feels *understood*, not just obeyed.
*   **Security Note:** All temp logs from tool calls (especially `clarify` outputs) must be aggressively scrubbed to prevent secret leakage.

---

## 5. Code Philosophy (Hackability)

Chambers is a **living codebase**.

*   **No ORMs:** Direct `sqlite3` calls.
*   **No Frameworks:** Pure `textual` and `requests`.
*   **Flat Structure:** No deep nesting. `chambers/app.py`, `chambers/session.py`.
*   **Readable:** If we can't read the whole codebase in 10 minutes, we over-engineered it.

### Testing Philosophy:
*   **Manual First:** We are the QA team. Automated tests come after we've used it.
*   **Integration > Unit:** Test the full flow (TUI → API → DB), not individual functions.
*   **Mock for Speed:** Use mock Blacksmith MCP responses for offline dev/testing.

---

## 6. Implementation Roadmap

### Phase 1: The Foundation (Skeleton)
*   [ ] **Project Setup:** `chambers/` dir, `venv`, requirements.
*   [ ] **TUI Core:** Basic Textual app with ChatPanel, Input, and StatusBar.
*   [ ] **Session DB:** SQLite schema (Sessions, Messages). WAL mode enabled.
*   [ ] **Single-AI Loop:** Connect Claude (Anthropic API). Streaming response.
*   [ ] **Command Parser:** Implement `/help`, `/quit`.

### Phase 2: The Council (Multi-AI)
*   [ ] **API Integrations:** Add Gemini (Google) and Grok (xAI) clients.
*   [ ] **Turn Coordinator:** Implement Round-Robin and `/phase` toggle.
*   [ ] **Async Queue:** Allow Vinga to type while AIs are generating.
*   [ ] **Mermaid Support:** Implement ASCII fallback renderer.
*   [ ] **Model Fallbacks:** Try fallback model if primary fails/deprecated.

### Phase 3: The Brain (Blacksmith Integration)
*   [ ] **Blacksmith Client:** Implement the interface to `context_core_mcp`.
*   [ ] **Tool Interception:** Build logic to detect `project.query...` calls.
*   [ ] **Clarification Tool:** Implement the `clarify()` pause-and-ask flow.
*   [ ] **Manual Indexing:** Add `/reindex @file`.

### Phase 4: The Memory (Context Budgeting)
*   [ ] **Token Counting:** Integrate `tiktoken` for budget tracking.
*   [ ] **Checkpoint System:** Implement "Hot" -> "Summary" rollover.
*   [ ] **Summarizer:** Routine to summarize dropped message blocks (Async).
*   [ ] **Debug Command:** Implement `/debug` to dump context budgets and session state.

### Phase 5: The Sentry & Polish
*   [ ] **Blacksmith Sentry:** Implement `watchdog` for auto-indexing.
*   [ ] **Resume & Export:** Full `/resume` and `/export`.
*   [ ] **Metrics Logging:** Optional perf metrics (latency, rollovers) if enabled.
*   [ ] **Visual Polish:** Themes, spinners, error UX.

---

## 7. Configuration Schema (`config.yml`)

```yaml
app:
  name: "SKYFORGE Chambers"
  theme: "dark_protocol"

context:
  budget:
    pinned: 15000
    history: 20000
    hot: 20000
    on_demand: 5000
  auto_load:
    - "plan.md"
    - "PLANNING_FRAMEWORK.md"

latency:
  blacksmith_timeout_ms: 3000
  summarize_async: true

observability:
  enable_metrics: false  # Opt-in for performance logging
  log_path: "~/.chambers/metrics.log"

blacksmith:
  mcp_url: "http://localhost:8000"
  auto_index_on_write: true
  enable_sentry: true

ai_models:
  claude:
    enabled: true
    model: "claude-3-5-sonnet"
    fallback: "claude-3-sonnet"
  gemini:
    enabled: true
    model: "gemini-1.5-pro"
    fallback: "gemini-1.0-pro"
  grok:
    enabled: true
    model: "grok-beta"
    fallback: null
```

---

## 8. Collaboration Credits
*   **Architects:** Vinga, Claude, Gemini, Grok
*   **Core Inspiration:** The Blacksmith Project & The Mutual Growth Mandate
