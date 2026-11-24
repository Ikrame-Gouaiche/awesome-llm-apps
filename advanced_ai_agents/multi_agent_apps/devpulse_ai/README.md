# 🧠 DevPulseAI — Client-Tailored & Cost-Governed Signal Intelligence

An enhanced multi-agent signal intelligence pipeline built on [`devpulse_ai`](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_ai_agents/multi_agent_apps/devpulse_ai), upgraded for **domain-specific relevance**, **OpenRouter LLM routing**, and **deterministic cost governance**.

---

## 1. Project Overview & Baseline Architecture (Before Changes)

`devpulse_ai` is a multi-agent signal intelligence pipeline that collects public technical updates from five developer sources (**GitHub**, **ArXiv**, **HackerNews**, **Medium**, and **HuggingFace**), scores them for relevance, assesses operational/security risks, and produces a prioritized intelligence digest.

Its defining architectural rule is:
> **Agents are used only where reasoning is required.** Deterministic operations (fetching, schema normalization, deduplication) are implemented as plain utilities — not agents.

### Baseline Pipeline (Before Changes)

```text
[Adapters: GitHub, ArXiv, HackerNews, Medium, HuggingFace]
                         │  (raw heterogeneous dicts)
                         ▼
         SignalCollector (Utility — no LLM)
         • Normalizes schema & deduplicates via "source:id"
                         │  (normalized signals)
                         ▼
         RelevanceAgent (Agent — MODEL_RELEVANCE, default: gpt-4.1-mini)
         • Scores 0–100 + 1-sentence reason (falls back to star/point heuristics)
                         │  (scored signals)
                         ▼
         RiskAgent (Agent — MODEL_RISK, default: gpt-4.1-mini)
         • Rates LOW / MEDIUM / HIGH / CRITICAL + breaking_changes bool
         • Falls back to title-keyword scan
                         │  (risk-assessed signals)
                         ▼
         SynthesisAgent (Agent — MODEL_SYNTHESIS, default: gpt-4.1)
         • Prioritizes via relevance * risk_multiplier, groups by source, outputs digest
```

### Baseline File Map (Before Changes)

| File | Role | Baseline Behavior |
|---|---|---|
| `adapters/github.py` | Data fetcher | Queries GitHub Search API for repos created in the last 24h |
| `adapters/arxiv.py` | Data fetcher | Hardcoded to `cat:cs.AI OR cat:cs.LG` Atom XML |
| `adapters/hackernews.py` | Data fetcher | Hardcoded to Algolia query `"AI OR LLM OR Machine Learning OR GPT"` |
| `adapters/medium.py` | Data fetcher | Parses 4 hardcoded RSS feeds (AI, ML, Netflix Tech, Meta Eng) |
| `adapters/huggingface.py` | Data fetcher | Fetches top liked models from `huggingface.co/api/models` |
| `agents/signal_collector.py` | Deterministic utility | Deduplicates via `f"{source}:{id}"` and normalizes fields |
| `agents/relevance_agent.py` | LLM classifier | Hardcoded for `"AI/ML developers"`, uses `OpenAIChat` |
| `agents/risk_agent.py` | LLM analyzer | Evaluates vulnerabilities/breaking changes unconditionally on every signal |
| `agents/synthesis_agent.py` | Digest builder | Prioritizes via `relevance * risk_multiplier` and formats summary |
| `main.py` / `streamlit_app.py` | Runners | CLI pipeline & Streamlit dashboard |
| `verify.py` | Offline test suite | 5 mock-data verification checks (no API keys required) |

---

## 2. Why I Chose This Project to Upgrade

This codebase aligns directly with **AI Forward Deployed Engineering (FDE)** principles and production AI engineering best practices:

- **Honest Agent Boundaries:** It already separates deterministic work (`SignalCollector`) from reasoning work (`RelevanceAgent`, `RiskAgent`, `SynthesisAgent`) instead of wrapping simple loops in unnecessary LLM calls.
- **Enterprise-Relevant Use Case:** Technical teams across AI/ML, FinTech Compliance, Cloud Infrastructure, and DevSecOps all face signal overload and need tailored, risk-aware briefings rather than generic news feeds.
- **High-Leverage Upgrade Surface:** With targeted, minimal changes (~5–10% codebase scope), the pipeline can demonstrate **no vendor lock-in**, **client customization**, **deterministic LLM cost reduction**, and **graceful offline verification**.

---

## 3. Problems / Gaps Identified & Objective

### Baseline Gaps Found During Code Review

1. **Single-Provider Lock-In (`OpenAIChat` only):** All three agents instantiated `OpenAIChat(id=...)` targeting OpenAI directly, with no OpenRouter routing or `.env` loading in `streamlit_app.py` / `main.py`.
2. **Hardcoded AI/ML Persona & Queries:** `RelevanceAgent` scored every item for `"AI/ML developers"`, while `arxiv.py`, `hackernews.py`, and `medium.py` used hardcoded AI/ML queries—making non-AI domains inaccurate.
3. **Unconditional `RiskAgent` Calls (Wasted LLM Tokens):** `RiskAgent.assess_batch()` ran an LLM call on **every** collected signal, including low-relevance noise (`0–30`).
4. **No Fallback Telemetry & Priority Ordering Bugs:**
   - Neither `RelevanceAgent` nor `RiskAgent` recorded whether a result came from the LLM or heuristic fallback (`used_fallback`).
   - `streamlit_app.py` iterated over raw `assessed` order instead of sorting by relevance, imported heavy `agno` dependencies at module top-level (stalling initial UI render ~40s), and referenced a missing `assets/logo.png` image.

### Objective

Upgrade `devpulse_ai` into a **Client-Tailored & Cost-Governed Signal Intelligence** pipeline while keeping the implementation clean, simple, and 100% compatible with offline verification (`python verify.py`):
- Support **OpenRouter** (`google/gemini-2.5-flash-lite` by default) with `.env` loading and zero leaked secrets.
- Make **both source fetching and relevance/risk scoring dynamic** based on a user-selected **Target Domain** preset.
- Add a **deterministic cost gate** (with a critical security-keyword bypass) before `RiskAgent` so noisy signals never trigger unnecessary LLM calls.
- Keep the Streamlit UI fast and responsive on startup.

---

## 4. Enhancements Implemented

### 4.1 OpenRouter Integration & `.env` Loading
- Updated `RelevanceAgent`, `RiskAgent`, and `SynthesisAgent` to route `OpenAIChat` through OpenRouter (`https://openrouter.ai/api/v1`) using `OPENROUTER_API_KEY` and `google/gemini-2.5-flash-lite` as the default low-cost model.
- Added `load_dotenv()` in both `streamlit_app.py` and `main.py` before importing agents, and verified `.env` is ignored via `.gitignore`.

```python
# agents/relevance_agent.py
DEFAULT_MODEL = os.environ.get("MODEL_RELEVANCE", "google/gemini-2.5-flash-lite")

self.agent = Agent(
    name="Relevance Scorer",
    # Route OpenAIChat through OpenRouter's OpenAI-compatible API
    model=OpenAIChat(
        id=self.model_id,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    ),
    ...
)
```

### 4.2 Domain Presets & Domain-Aligned Source Adapters (`config.py` + `adapters/`)
- Created `config.py` with `DomainProfile` and `DOMAIN_PRESETS` for 5 domains tailored to the existing sources:
  - **AI/ML Engineering** *(default)*
  - **FinTech Compliance**
  - **Cloud Infrastructure**
  - **Cybersecurity & DevSecOps**
  - **Data & Backend Engineering**
- Updated `adapters/github.py`, `adapters/arxiv.py`, `adapters/hackernews.py`, and `adapters/medium.py` to accept optional domain queries/feeds while preserving their original defaults.

```python
# config.py
@dataclass(frozen=True)
class DomainProfile:
    """Configuration defining a target domain for signal collection and relevance scoring."""
    name: str
    domain_focus: str
    tech_stack: Tuple[str, ...]
    fallback_keywords: Tuple[str, ...]
    github_query: Optional[str]
    arxiv_query: str
    hn_query: str
    medium_feeds: Tuple[str, ...]
    huggingface_supported: bool = False
```

### 4.3 Dynamic Domain Relevance & Fallback Tracking (`agents/relevance_agent.py`)
- Updated `RelevanceAgent` to inject `profile.name`, `profile.domain_focus`, and `profile.tech_stack` into both agent instructions and `build_prompt()`.
- Updated `_fallback_score()` to match domain keywords against `title + description` alongside stars/points, and added `"used_fallback": True/False` tracking on every scored signal.

```python
# agents/relevance_agent.py
def build_prompt(self, signal: Dict[str, Any], profile: Optional[DomainProfile] = None) -> str:
    """Build a domain-tailored relevance scoring prompt for a signal."""
    active_profile = profile or self.profile
    stack_str = ", ".join(active_profile.tech_stack)
    return f"""Rate the relevance of this signal for the '{active_profile.name}' domain.
Domain Focus: {active_profile.domain_focus}
Key Technologies / Topics: {stack_str}
..."""
```

### 4.4 Client-Aware Risk Prompts & Deterministic Cost Gate (`agents/risk_agent.py` + `agents/synthesis_agent.py`)
- Updated `RiskAgent` to accept `profile` and contextualize security/breaking-change analysis for the chosen domain's stack, tracking `"used_fallback"` and `"gated"`.
- Added a deterministic relevance gate in `RiskAgent.assess_batch(signals, min_relevance=50)` with a safety bypass for critical security keywords (`cve`, `vulnerability`, `exploit`, `breach`, `zero-day`, `rce`):

```python
# agents/risk_agent.py
CRITICAL_BYPASS_KEYWORDS = ("cve", "vulnerability", "exploit", "breach", "zero-day", "rce")

def assess_batch(
    self, signals: List[Dict[str, Any]], min_relevance: int = 50
) -> List[Dict[str, Any]]:
    """Assess risks, skipping low-relevance noise unless a critical keyword is present."""
    assessed = []
    for signal in signals:
        score = signal.get("relevance", {}).get("score", 50)
        text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()
        has_critical_keyword = any(kw in text for kw in self.CRITICAL_BYPASS_KEYWORDS)

        if score < min_relevance and not has_critical_keyword:
            result = {
                "risk_level": "SKIPPED",
                "concerns": [f"Skipped by cost gate (relevance {score} < {min_relevance})"],
                "breaking_changes": False,
                "gated": True,
                "used_fallback": False,
            }
        else:
            result = self.assess(signal)

        assessed.append({**signal, "risk": result})
    return assessed
```

- Updated `SynthesisAgent._prioritize_signals()` to include `"SKIPPED": 0.5` in `risk_multiplier` so gated low-relevance items sort below `"LOW": 0.8`.

### 4.5 Fast, Domain-Aware UI & CLI (`streamlit_app.py` + `main.py`)
- **Preset Domain Dropdown:** Added a preset-only `Target Domain` selectbox in `streamlit_app.py` and `--domain` CLI flag in `main.py`.
- **Priority Ordering & Styling:** Sorted displayed signals by descending relevance score and added `.risk-skipped` badge styling.
- **Fast Startup Fix:** Moved `st.set_page_config(...)` to the top of `streamlit_app.py`, lazy-loaded heavy `agents` imports (`agno`/`openai`) inside the Run button handler, and removed the missing `assets/logo.png` call so the UI renders immediately instead of stalling on a blank page.

### 4.6 Expanded Offline Verification (`verify.py`)
- Extended `verify.py` with check `[6/6] Verifying Dynamic Domain Relevance & Presets` to validate all 5 domain presets, domain-specific fallback scoring, `"used_fallback"` flags, `"SKIPPED"` cost gating, and critical-keyword (`CVE`) bypass offline:

```text
[1/5] Verifying imports...
  ✓ All modules imported successfully
  ✓ SignalCollector confirmed as utility (no LLM)
[2/5] Verifying Signal Collector (utility)...
  ✓ Collected 5 signals: 1 from github, 1 from arxiv, 1 from hackernews, 1 from medium, 1 from huggingface
  ✓ Deduplication works correctly
[3/5] Verifying Relevance Agent (fallback mode)...
  ✓ Scored 5 signals (heuristic fallback)
[4/5] Verifying Risk Agent (fallback mode)...
  ✓ Assessed 5 signals (1 with breaking changes)
[5/5] Verifying Synthesis Agent...
  ✓ Generated digest with 2 recommendations
[6/6] Verifying Dynamic Domain Relevance & Presets...
  ✓ Verified 5 domain presets + cost gate (Cloud=80, FinTech=80 vs off-domain=35)
```

---

## How to Run

### 1. Offline Verification (No API Key Required)
```powershell
python verify.py
```

### 2. CLI Pipeline (With OpenRouter)
Create a `.env` file (ignored by git):
```env
OPENROUTER_API_KEY=sk-or-v1-...
MODEL_RELEVANCE=google/gemini-2.5-flash-lite
MODEL_RISK=google/gemini-2.5-flash-lite
MODEL_SYNTHESIS=google/gemini-2.5-flash-lite
```
Run with a specific domain preset:
```powershell
python main.py --domain "Cloud Infrastructure"
```

### 3. Streamlit Dashboard
```powershell
python -m streamlit run streamlit_app.py
```
Then open `http://localhost:8501`, select a **Target Domain** and **Signal Sources** in the sidebar, and click **🚀 Run Intelligence Pipeline**.
