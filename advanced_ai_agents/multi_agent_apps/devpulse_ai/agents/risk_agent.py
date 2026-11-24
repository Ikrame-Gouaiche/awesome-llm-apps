"""
Risk Agent — Assesses security risks and breaking changes.

This agent uses LLM reasoning to analyze signals for potential risks
including security vulnerabilities, breaking API changes, and deprecation
notices. It's a legitimate agent because risk assessment requires
contextual understanding of technical implications.

Model Selection:
    Uses a structured-reasoning model (gpt-4.1-mini by default) because
    risk assessment benefits from careful, step-by-step analysis. For
    production workloads with high-stakes decisions, consider upgrading
    to gpt-4.1 or o4-mini via the MODEL_RISK environment variable.
"""

import json
from typing import Dict, Any, List, Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from config import DomainProfile, get_domain_profile

# Central model config — override via MODEL_RISK env var
import os
DEFAULT_MODEL = os.environ.get("MODEL_RISK", "google/gemini-2.5-flash-lite")


class RiskAgent:
    """
    Agent that assesses risk levels in technical signals.

    Why this IS an agent:
        Risk assessment requires reasoning about technical implications,
        understanding security contexts, and making judgment calls about
        severity. This is inherently a reasoning task.

    Responsibilities:
    - Identify security vulnerabilities
    - Flag breaking changes
    - Detect deprecation notices
    - Rate overall risk level (LOW / MEDIUM / HIGH / CRITICAL)
    """

    RISK_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    CRITICAL_BYPASS_KEYWORDS = ("cve", "vulnerability", "exploit", "breach", "zero-day", "rce")

    def __init__(self, model_id: Optional[str] = None, profile: Optional[DomainProfile] = None):
        """
        Initialize the Risk Agent.

        Args:
            model_id: OpenAI/OpenRouter model to use. Defaults to MODEL_RISK.
            profile: Optional DomainProfile to tailor risk assessment.
        """
        self.model_id = model_id or DEFAULT_MODEL
        self.profile = profile or get_domain_profile()
        stack_str = ", ".join(self.profile.tech_stack)
        self.agent = Agent(
            name="Risk Assessor",
            # Route OpenAIChat through OpenRouter's OpenAI-compatible API
            model=OpenAIChat(
                id=self.model_id,
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
            ),
            role=f"Assesses security and breaking change risks for {self.profile.name}",
            instructions=[
                "Analyze signals for security vulnerabilities.",
                "Identify breaking changes that may affect developers.",
                "Flag deprecation notices and migration requirements.",
                f"Evaluate impact in the context of {self.profile.name} ({stack_str}).",
                "Rate risk level: LOW, MEDIUM, HIGH, or CRITICAL.",
            ],
            markdown=True,
        )

    def assess(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk level of a signal.

        Attempts LLM assessment first, falls back to keyword heuristics.
        """
        stack_str = ", ".join(self.profile.tech_stack)
        prompt = f"""Analyze this technical signal for risks in the '{self.profile.name}' domain:
Domain Focus: {self.profile.domain_focus}
Key Stack: {stack_str}

Signal:
- Source: {signal.get('source', 'unknown')}
- Title: {signal.get('title', 'Untitled')}
- Description: {signal.get('description', '')[:500]}

Assess for:
1. Security vulnerabilities
2. Breaking changes
3. Deprecations

Respond with ONLY a JSON object:
{{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "concerns": ["<list of concerns>"], "breaking_changes": true|false}}"""

        try:
            response = self.agent.run(prompt, stream=False)
            return self._parse_response(response.content, signal)
        except Exception as e:
            return self._fallback_assessment(signal, str(e))

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

    def _parse_response(self, content: str, signal: Dict) -> Dict[str, Any]:
        """Parse LLM JSON response into structured output."""
        try:
            text = content.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            parsed = json.loads(text)
            parsed["gated"] = False
            parsed["used_fallback"] = False
            return parsed
        except (json.JSONDecodeError, IndexError):
            return self._fallback_assessment(signal, "Parse error")

    def _fallback_assessment(self, signal: Dict, error: str) -> Dict[str, Any]:
        """
        Keyword-based fallback when LLM is unavailable.

        Simple heuristic: scan title for risk-indicating keywords.
        This is intentionally conservative — better to over-flag than miss.
        """
        title = signal.get("title", "").lower()

        risk_level = "LOW"
        concerns = []

        risk_keywords = {
            "HIGH": ["vulnerability", "exploit", "cve", "critical", "breach"],
            "MEDIUM": ["breaking", "deprecated", "removed", "migration"],
        }

        for level, keywords in risk_keywords.items():
            if any(kw in title for kw in keywords):
                risk_level = level
                concerns.append(f"Keyword match: {level}")
                break

        return {
            "risk_level": risk_level,
            "concerns": concerns or [f"Heuristic (LLM unavailable: {error})"],
            "breaking_changes": "breaking" in title,
            "gated": False,
            "used_fallback": True,
        }
