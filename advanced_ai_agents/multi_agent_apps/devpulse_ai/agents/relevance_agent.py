"""
Relevance Agent — Scores signals by developer relevance (0–100).

This agent uses LLM reasoning to evaluate each signal's importance to
AI/ML developers. It's a legitimate agent because relevance scoring
requires judgment, context understanding, and nuanced assessment that
pure heuristics cannot capture.

Model Selection:
    Uses a fast, cost-efficient model (gpt-4.1-mini by default) because
    relevance scoring is high-volume and doesn't require deep reasoning —
    it's a classification task, not a synthesis task.
"""

import json
from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from config import DomainProfile, get_domain_profile

# Central model config — override via MODEL_RELEVANCE env var
import os
DEFAULT_MODEL = os.environ.get("MODEL_RELEVANCE", "google/gemini-2.5-flash-lite")


class RelevanceAgent:
    """
    Agent that scores signals based on relevance to a chosen technical domain.

    Why this IS an agent (unlike SignalCollector):
        Relevance scoring requires understanding context, assessing novelty,
        and making judgment calls about what matters to a target domain. This is
        inherently a reasoning task that benefits from LLM capabilities.

    Responsibilities:
    - Score signals 0–100 based on domain-specific relevance
    - Provide reasoning for each score
    - Gracefully fall back to domain-aware heuristics when LLM unavailable
    """

    def __init__(self, model_id: Optional[str] = None, profile: Optional[DomainProfile] = None):
        """
        Initialize the Relevance Agent.

        Args:
            model_id: Model ID to use via OpenRouter. Defaults to MODEL_RELEVANCE.
            profile: Target DomainProfile for scoring. Defaults to AI/ML Engineering.
        """
        self.model_id = model_id or DEFAULT_MODEL
        self.profile = profile or get_domain_profile()
        stack_str = ", ".join(self.profile.tech_stack)
        self.agent = Agent(
            name="Relevance Scorer",
            # Route OpenAIChat through OpenRouter's OpenAI-compatible API
            model=OpenAIChat(
                id=self.model_id,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
            ),
            role=f"Scores technical signals for relevance to {self.profile.name}",
            instructions=[
                "Score each signal from 0-100 based on relevance to the target domain.",
                "Consider: novelty, impact, actionability, and timeliness.",
                f"Target domain: {self.profile.name} — {self.profile.domain_focus}.",
                f"Prioritize signals relevant to this stack: {stack_str}.",
                "Provide brief reasoning for each score.",
            ],
            markdown=True,
        )

    def build_prompt(self, signal: Dict[str, Any], profile: Optional[DomainProfile] = None) -> str:
        """Build a domain-tailored relevance scoring prompt for a signal."""
        active_profile = profile or self.profile
        stack_str = ", ".join(active_profile.tech_stack)
        return f"""Rate the relevance of this signal for the '{active_profile.name}' domain.
Domain Focus: {active_profile.domain_focus}
Key Technologies / Topics: {stack_str}

Score from 0-100 where:
- 0-30: Low relevance (off-topic or noise for {active_profile.name})
- 31-60: Moderate relevance (tangentially useful, not urgent)
- 61-80: High relevance (important for {active_profile.name} practitioners)
- 81-100: Critical relevance (must-know, directly actionable for {active_profile.name})

Signal:
- Source: {signal.get('source', 'unknown')}
- Title: {signal.get('title', 'Untitled')}
- Description: {signal.get('description', '')[:500]}

Respond with ONLY a JSON object:
{{"score": <number>, "reasoning": "<one sentence>"}}"""

    def score(self, signal: Dict[str, Any], profile: Optional[DomainProfile] = None) -> Dict[str, Any]:
        """
        Score a single signal for domain-specific relevance.

        Attempts LLM scoring first, falls back to heuristics on failure.
        """
        active_profile = profile or self.profile
        prompt = self.build_prompt(signal, profile=active_profile)

        try:
            response = self.agent.run(prompt, stream=False)
            return self._parse_response(response.content, signal, profile=active_profile)
        except Exception as e:
            return self._fallback_score(signal, str(e), profile=active_profile)

    def score_batch(
        self, signals: List[Dict[str, Any]], profile: Optional[DomainProfile] = None
    ) -> List[Dict[str, Any]]:
        """Score multiple signals, returning each with a 'relevance' key."""
        active_profile = profile or self.profile
        scored = []
        for signal in signals:
            result = self.score(signal, profile=active_profile)
            scored.append({**signal, "relevance": result})
        return scored

    def _parse_response(
        self, content: str, signal: Dict, profile: Optional[DomainProfile] = None
    ) -> Dict[str, Any]:
        """Parse LLM JSON response into structured output."""
        active_profile = profile or self.profile
        try:
            text = content.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            parsed = json.loads(text)
            parsed["score"] = max(0, min(100, int(round(float(parsed["score"])))))
            parsed["used_fallback"] = False
            return parsed
        except (json.JSONDecodeError, IndexError, KeyError, TypeError, ValueError):
            return self._fallback_score(signal, "Parse error", profile=active_profile)

    def _fallback_score(
        self, signal: Dict, error: str, profile: Optional[DomainProfile] = None
    ) -> Dict[str, Any]:
        """
        Domain-aware heuristic fallback when LLM is unavailable.

        Combines domain keyword matching against title/description with
        metadata popularity proxies (stars, points).
        """
        active_profile = profile or self.profile
        text = f"{signal.get('title', '')} {signal.get('description', '')}".lower()
        keywords = {kw.lower() for kw in (*active_profile.fallback_keywords, *active_profile.tech_stack)}
        matched = sorted(kw for kw in keywords if kw in text)

        score = 35  # Base score when domain keywords are absent
        score += min(len(matched) * 15, 45)

        metadata = signal.get("metadata", {})
        if metadata.get("stars", 0) > 100:
            score += 15
        if metadata.get("points", 0) > 50:
            score += 10

        match_note = f"; matched [{', '.join(matched[:4])}]" if matched else "; no direct domain keywords"
        return {
            "score": min(score, 100),
            "reasoning": f"Heuristic score for {active_profile.name}{match_note} (LLM unavailable: {error})",
            "used_fallback": True,
        }
