"""
DevPulseAI — Multi-Agent Signal Intelligence Pipeline

Demonstrates a production-style multi-agent workflow that aggregates
technical signals from multiple sources, scores them for relevance,
assesses risks, and synthesizes an actionable intelligence digest.

Architecture:
    Adapters (fetch) → SignalCollector (normalize) → RelevanceAgent (score)
    → RiskAgent (assess) → SynthesisAgent (digest)

Design Decisions:
    - Signal collection is a utility, not an agent (deterministic work).
    - Agents are used only where reasoning is required.
    - Single provider (OpenAI) by default to reduce onboarding friction.
    - Models are chosen by role: fast for classification, strong for synthesis.

Usage:
    export OPENAI_API_KEY=sk-...
    python main.py

    Without API key: agents fall back to heuristic scoring.
"""

import argparse
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Reduced default signal count for faster demo execution
DEFAULT_SIGNAL_LIMIT = 5

from config import DOMAIN_PRESETS, DomainProfile, get_domain_profile

# Import adapters
from adapters.github import fetch_github_trending
from adapters.arxiv import fetch_arxiv_papers
from adapters.hackernews import fetch_hackernews_stories
from adapters.medium import fetch_medium_blogs
from adapters.huggingface import fetch_huggingface_models

# Import pipeline components
from agents import (
    SignalCollector,  # Utility — no LLM
    RelevanceAgent,   # Agent — OpenRouter
    RiskAgent,        # Agent — OpenRouter
    SynthesisAgent,   # Agent — OpenRouter
)


def collect_signals(
    limit: Optional[int] = None,
    profile: Optional[DomainProfile] = None,
) -> List[Dict[str, Any]]:
    """
    Collect signals from all configured sources for the given domain profile.

    This is pure data aggregation — no LLM involved.
    """
    active_profile = profile or get_domain_profile()
    fetch_limit = limit if limit is not None else DEFAULT_SIGNAL_LIMIT
    print(
        f"\n📡 [1/4] Collecting Signals for '{active_profile.name}' "
        f"(limit: {fetch_limit} per source)..."
    )

    signals = []

    print("  → Fetching GitHub trending repos...")
    signals.extend(fetch_github_trending(limit=fetch_limit, query=active_profile.github_query))

    print("  → Fetching ArXiv papers...")
    signals.extend(fetch_arxiv_papers(limit=fetch_limit, search_query=active_profile.arxiv_query))

    print("  → Fetching HackerNews stories...")
    signals.extend(fetch_hackernews_stories(limit=fetch_limit, query=active_profile.hn_query))

    print("  → Fetching Medium blogs...")
    signals.extend(
        fetch_medium_blogs(limit=min(fetch_limit, 3), feeds=active_profile.medium_feeds)
    )

    if active_profile.huggingface_supported:
        print("  → Fetching HuggingFace models...")
        signals.extend(fetch_huggingface_models(limit=fetch_limit))

    print(f"  ✓ Collected {len(signals)} raw signals")
    return signals


def run_pipeline(domain: Optional[str] = None):
    """
    Execute the full signal intelligence pipeline for a target domain.

    Pipeline stages:
    1. Signal Collection — Aggregate from domain-aligned sources (utility, no LLM)
    2. Normalization    — Deduplicate and normalize (utility, no LLM)
    3. Relevance Score  — Rate signals 0-100 for chosen domain (agent)
    4. Risk Assessment  — Identify risks (agent)
    5. Synthesis        — Produce digest (agent)
    """
    profile = get_domain_profile(domain)

    print("=" * 60)
    print(f"🧠 DevPulseAI — Signal Intelligence Pipeline ({profile.name})")
    print("=" * 60)

    # Check for API key
    if not (os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        print("\n⚠️  Warning: OPENROUTER_API_KEY not set.")
        print("   Agents will use fallback heuristics.\n")

    # Stage 1: Collect raw signals from adapters
    raw_signals = collect_signals(profile=profile)

    # Stage 2: Normalize and deduplicate (utility — no LLM)
    collector = SignalCollector()
    print("\n🔄 [2/4] Normalizing Signals...")
    normalized = collector.collect(raw_signals)
    print(f"  ✓ {collector.summarize_collection(normalized)}")

    # Stage 3: Score for domain-specific relevance
    relevance = RelevanceAgent(profile=profile)
    print(f"\n📊 [3/4] Scoring Relevance for '{profile.name}'...")
    scored = relevance.score_batch(normalized)
    high_relevance = sum(
        1 for s in scored if s.get("relevance", {}).get("score", 0) >= 70
    )
    print(f"  ✓ {high_relevance}/{len(scored)} signals rated high-relevance")

    # Stage 4: Assess risks (agent — gpt-4.1-mini)
    risk = RiskAgent()
    print("\n⚠️  [4/4] Assessing Risks...")
    assessed = risk.assess_batch(scored)
    critical = sum(
        1
        for s in assessed
        if s.get("risk", {}).get("risk_level") in ["HIGH", "CRITICAL"]
    )
    print(f"  ✓ {critical}/{len(assessed)} signals with elevated risk")

    # Stage 5: Synthesize digest (agent — gpt-4.1)
    synthesis = SynthesisAgent()
    print("\n📋 Generating Intelligence Digest...")
    digest = synthesis.synthesize(assessed)

    # Output results
    print("\n" + "=" * 60)
    print("📄 INTELLIGENCE DIGEST")
    print("=" * 60)
    print(f"\n🕐 Generated: {digest['generated_at']}")
    print(f"📦 Total Signals: {digest['total_signals']}")
    print(f"\n📝 Summary: {digest['executive_summary']}")

    print("\n🎯 Top Priority Signals:")
    for i, signal in enumerate(digest.get("priority_signals", [])[:3], 1):
        score = signal.get("relevance", {}).get("score", "?")
        risk_level = signal.get("risk", {}).get("risk_level", "?")
        print(f"   {i}. [{signal['source']}] {signal['title'][:50]}...")
        print(f"      Relevance: {score} | Risk: {risk_level}")

    print("\n💡 Recommendations:")
    for rec in digest.get("recommendations", []):
        print(f"   • {rec}")

    print("\n" + "=" * 60)
    print("✅ Pipeline completed successfully!")
    print("=" * 60)

    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevPulseAI Signal Intelligence Pipeline")
    parser.add_argument(
        "--domain",
        choices=list(DOMAIN_PRESETS.keys()),
        default=None,
        help="Target domain for source filtering and relevance scoring",
    )
    args = parser.parse_args()
    run_pipeline(domain=args.domain)
