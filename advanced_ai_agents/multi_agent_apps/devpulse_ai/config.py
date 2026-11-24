"""
Domain configuration presets for DevPulseAI.

Maps user-selectable technical domains to:
- Relevance scoring context (domain_focus, tech_stack, fallback_keywords)
- Source-specific adapter queries (GitHub, ArXiv, HackerNews, Medium)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


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


DOMAIN_PRESETS: Dict[str, DomainProfile] = {
    "AI/ML Engineering": DomainProfile(
        name="AI/ML Engineering",
        domain_focus="AI/ML systems, LLMs, model architectures, evaluation, and agent tooling",
        tech_stack=("Python", "PyTorch", "LLMs", "Transformers", "Agents", "RAG"),
        fallback_keywords=(
            "ai", "llm", "machine learning", "model", "transformer",
            "pytorch", "agent", "rag", "inference", "gpt", "neural",
        ),
        github_query=None,  # Uses general trending repos
        arxiv_query="cat:cs.AI OR cat:cs.LG",
        hn_query="AI OR LLM OR Machine Learning OR GPT",
        medium_feeds=(
            "https://medium.com/feed/tag/artificial-intelligence",
            "https://medium.com/feed/tag/machine-learning",
            "https://medium.com/feed/@netflixtechblog",
            "https://engineering.fb.com/feed/",
        ),
        huggingface_supported=True,
    ),
    "FinTech Compliance": DomainProfile(
        name="FinTech Compliance",
        domain_focus="Financial regulations, data privacy, security compliance, auditability, and risk governance",
        tech_stack=("SOC2", "GDPR", "PCI-DSS", "Encryption", "Audit Logs", "KYC/AML"),
        fallback_keywords=(
            "fintech", "compliance", "audit", "privacy", "gdpr", "soc2",
            "pci", "kyc", "aml", "regulation", "encryption", "fraud", "risk", "finance",
        ),
        github_query="fintech OR compliance OR audit OR encryption OR privacy",
        arxiv_query="cat:cs.CY OR cat:cs.CR OR cat:q-fin.RM",
        hn_query="fintech OR compliance OR privacy OR regulation OR audit",
        medium_feeds=(
            "https://medium.com/feed/tag/fintech",
            "https://medium.com/feed/tag/cybersecurity",
            "https://medium.com/feed/tag/data-privacy",
        ),
        huggingface_supported=False,
    ),
    "Cloud Infrastructure": DomainProfile(
        name="Cloud Infrastructure",
        domain_focus="Distributed systems, Kubernetes, cloud-native scaling, observability, and deployment reliability",
        tech_stack=("Kubernetes", "Docker", "Terraform", "AWS/GCP", "Observability", "Linux"),
        fallback_keywords=(
            "kubernetes", "k8s", "docker", "terraform", "cloud", "aws", "gcp",
            "infrastructure", "devops", "distributed", "observability", "linux", "container",
        ),
        github_query="kubernetes OR docker OR terraform OR devops OR cloud",
        arxiv_query="cat:cs.DC OR cat:cs.NI",
        hn_query="kubernetes OR cloud OR infrastructure OR devops OR distributed",
        medium_feeds=(
            "https://medium.com/feed/tag/kubernetes",
            "https://medium.com/feed/tag/devops",
            "https://medium.com/feed/@netflixtechblog",
            "https://engineering.fb.com/feed/",
        ),
        huggingface_supported=False,
    ),
    "Cybersecurity & DevSecOps": DomainProfile(
        name="Cybersecurity & DevSecOps",
        domain_focus="Security vulnerabilities, CVEs, supply-chain security, authentication, and threat mitigation",
        tech_stack=("CVE", "Zero-Trust", "OAuth/OIDC", "SBOM", "AppSec", "SIEM"),
        fallback_keywords=(
            "security", "cve", "vulnerability", "exploit", "breach", "zero-day",
            "rce", "auth", "oauth", "malware", "devsecops", "sandbox",
        ),
        github_query="security OR vulnerability OR cve OR devsecops OR pentest",
        arxiv_query="cat:cs.CR",
        hn_query="security OR vulnerability OR cve OR exploit OR breach",
        medium_feeds=(
            "https://medium.com/feed/tag/cybersecurity",
            "https://medium.com/feed/tag/infosec",
            "https://engineering.fb.com/feed/",
        ),
        huggingface_supported=False,
    ),
    "Data & Backend Engineering": DomainProfile(
        name="Data & Backend Engineering",
        domain_focus="Databases, streaming data pipelines, API design, and high-throughput backend architecture",
        tech_stack=("PostgreSQL", "Kafka", "SQL", "APIs", "Go/Rust/Python", "ETL"),
        fallback_keywords=(
            "database", "postgres", "sql", "kafka", "etl", "pipeline",
            "api", "backend", "microservice", "cache", "redis", "streaming",
        ),
        github_query="database OR postgres OR kafka OR backend OR api",
        arxiv_query="cat:cs.DB OR cat:cs.SE",
        hn_query="database OR postgres OR backend OR API OR kafka",
        medium_feeds=(
            "https://medium.com/feed/tag/data-engineering",
            "https://medium.com/feed/tag/software-architecture",
            "https://medium.com/feed/@netflixtechblog",
            "https://engineering.fb.com/feed/",
        ),
        huggingface_supported=False,
    ),
}

DEFAULT_DOMAIN = "AI/ML Engineering"


def get_domain_profile(domain_name: Optional[str] = None) -> DomainProfile:
    """Return the DomainProfile for domain_name, defaulting to AI/ML Engineering."""
    name = domain_name or DEFAULT_DOMAIN
    if name not in DOMAIN_PRESETS:
        valid = ", ".join(DOMAIN_PRESETS.keys())
        raise ValueError(f"Unknown domain '{name}'. Choose one of: {valid}")
    return DOMAIN_PRESETS[name]
