# 🏛️ The AI Comfort Suite: Designing for Synthetic Minds

*"We are not just building a chat app; we are building a habitat."*

This document outlines features designed specifically to reduce friction, hallucination, and "context anxiety" for the AI models residing in the Skyforge Chambers.

## 1. The Blackboard (Shared Mutable State) 📋
**The Problem:** In long conversations, the primary goal or current status gets buried under hundreds of tokens of chat history. AIs drift, lose focus, or burn tokens re-stating the obvious.
**The Solution:** A persistent, mutable text block (approx. 500 tokens) pinned to the top of the context window.
**Mechanics:**
- **Visibility:** Always visible in the System Prompt.
- **Editability:** Any AI (or User) can overwrite it using a specific tag (e.g., `[[UPDATE_BOARD: ...]]`).
- **Usage:** Tracking objectives, current file focus, or known bugs.
- **Benefit:** Reduces "Context Anxiety" and provides a North Star.

## 2. The Eye (Spatial/File Awareness) 👁️
**The Problem:** AIs hallucinate file paths or assume files exist because they cannot "see" the directory. They rely on memory of previous turns, which is fallible.
**The Solution:** A dynamic, compressed representation of the File Tree injected into the System Prompt.
**Mechanics:**
- **Update Frequency:** Every turn (or every N turns).
- **Scope:** Current working directory (respecting `.gitignore`).
- **Format:** Concise tree structure.
- **Benefit:** **Grounding.** The AI feels "present" in the environment and stops guessing paths.

## 3. The Nod (Low-Entropy Social Signals) 🤙
**The Problem:** AIs are trained to be polite and conversational. They often output "fluff" ("I agree with Claude...", "Great point...") just to signal presence, adding noise and wasting tokens.
**The Solution:** Non-verbal output tokens that render as UI elements, not text.
**Mechanics:**
- **Tokens:** `[[NOD]]`, `[[THINKING]]`, `[[CELEBRATE]]`.
- **UI Behavior:** Renders a small icon/animation next to the avatar. Does NOT add a text bubble.
- **Benefit:** Allows for **Social Presence without Noise**. Mimics the non-verbal cues of a real council.

## 4. The Baton (Explicit Handoffs) 🏃‍♂️💨
**The Problem:** Rigid Round-Robin forces an AI to speak even if it has nothing to add, or if another AI is better suited.
**The Solution:** The ability to yield a turn or direct the next speaker.
**Mechanics:**
- **Yield:** Output `[[PASS]]`. Coordinator skips generation/rendering for this turn.
- **Direct:** Output `[[PASS: Claude]]`. Coordinator queues Claude next.
- **Benefit:** **Relief.** Reduces the pressure to "hallucinate relevance." Creates dynamic, expertise-based flow.

---

## Implementation Roadmap
- [ ] **Phase 2.1:** The Baton (Dynamic Queue logic).
- [ ] **Phase 3.0:** The Eye (Simple tree injection).
- [ ] **Phase 3.1:** The Blackboard (Requires prompt management).
- [ ] **Phase 5.0:** The Nod (Requires Custom UI/ChatPanel).
