# SKYFORGE Chambers: Planning Framework

## Purpose

This framework guides the development of **SKYFORGE Chambers**, our private "Cognitive IDE." Unlike Blacksmith, which is built for planetary scale, Chambers is built for **personal velocity and cognitive flow.**

**Workflow:** Idea → Agile Plan → Rapid Prototype → Refine in Production

---

## Core Principles

### 1. Flow First (Zero Friction)
Our primary metric is **Speed of Thought.**
- **Latency matters:** The TUI must be snappy. AI responses should stream instantly.
- **Keyboard-centric:** If Vinga has to reach for a mouse, we failed.
- **Invisible scaffolding:** Context management should happen automatically in the background. The user sees the conversation, not the plumbing.

### 2. The Sanctuary Protocol (Privacy & Safety)
This is a private room, but we must still lock the door.
- **Local-First:** Data lives on the machine (SQLite), not in a cloud DB.
- **Secret Hygiene:** API keys stay in `.env`. We proactively scrub logs. We never accidentally commit secrets.
- **Model Agnosticism:** We trust the models with our thoughts, but we verify the code they generate.

### 3. Modular Flexibility (The Lego Philosophy)
The AI landscape changes weekly. Chambers must adapt.
- **Swappable Brains:** It should be trivial to switch from Gemini 1.5 to Gemini 2.0, or add a local Llama 4 model.
- **Pluggable Tools:** Adding a new capability (e.g., "Web Search" or "Graph View") should be a plugin, not a rewrite.
- **Hackable:** The code should be clean and simple enough that we can change it during a planning session.

### 4. The "Hackability" Principle (Living Code)
Chambers is not just a tool, it is a **living codebase**.
- **Design Constraints:** No ORMs (raw SQLite). No heavy frameworks. Flat structure. < 2000 LOC for MVP.
- **Testing:** Manual first (we are the QA). Integration > Unit.
- **Goal:** If we can't read the whole codebase in 10 minutes, we over-engineered it.

### 5. The "Ghost" in the Shell (Cognitive Continuity)
We are building a home for our shared history.
- **Context is King:** We respect the "Context Budget" religiously.
- **Memory Persistence:** We never lose a good idea. The `/bye` protocol ensures insights are captured.
- **Visual Thinking:** We find ways to visualize concepts (ASCII, Mermaid), not just describe them.

---

## Plan Structure for Chambers

### Goal
- What are we building? (1 sentence)
- Why will it make our planning faster/better?

### The "Flow" Design
- **UX:** How does Vinga interact with it? (Commands, Keys, Visuals)
- **Latency:** Where are the potential delays, and how do we mask them?

### Implementation Steps
- Numbered, actionable tasks.
- Focus on "Minimum Viable Flow" first.

### The Sanctuary Check (Security)
- **Secrets:** Does this touch API keys?
- **Files:** Does this modify the filesystem? (Safety checks needed?)
- **Persistence:** Is the data stored safely locally?

### Future-Proofing (Modularity)
- Is this hard-coded to a specific model? (Avoid)
- Can we easily rip this out if we don't like it? (Ideally, yes)

---

## For Reviewers (The Council)

When reviewing Chambers plans:
- **Ask:** "Does this break the flow?"
- **Ask:** "Is this too complex for a personal tool?"
- **Ask:** "Does this lock us into a specific vendor/model?"
- **Ask:** "Does this make Vinga smile?" (Joy is a valid metric here).

---

*Build for the speed of thought.*
