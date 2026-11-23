from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class CandidateProfile:
    name: str = "Garv Vaidya"
    degree: str = "B.Tech CSE"
    graduation_year: int = 2027
    college: str = "Hitkarini College of Engineering and Technology, Jabalpur"
    cgpa: float = 7.17
    location: str = "India"
    has_passport: bool = False
    portfolio_url: str = "https://garvvaidya.vercel.app"
    github_url: str = "https://github.com/kleeeoss"
    linkedin_url: str = "https://www.linkedin.com/in/garvaidya/"
    flagship_projects: List[str] = field(default_factory=lambda: [
        "Lucid-CI (AI DevSecOps GitHub App — Python/FastAPI + Docker/gVisor + Vertex AI + Go AST)",
        "Ares (K8s vector search engine)",
        "Leviathan (Distributed DAG orchestrator)"
    ])
    core_stack: List[str] = field(default_factory=lambda: [
        "Go", "Python", "FastAPI", "Docker", "gVisor", "Kubernetes", "AWS", "Linux",
        "Terraform", "Distributed Systems", "CI/CD Engines", "DevSecOps", "AST Sandbox", "Vertex AI", "Gemini", "AI Agents"
    ])

PROFILE = CandidateProfile()

# Compensation & Tier Constants
MIN_INTERN_STIPEND_INR = 10000
MAX_INTERN_STIPEND_CAP_INR = 50000

MIN_JOB_SALARY_LPA = 10.0
MAX_JOB_SALARY_CAP_LPA = 60.0

TOP_TIER_MIN_LPA = 20.0
TOP_TIER_MIN_STIPEND_INR = 30000

# Scoring Thresholds
MIN_SCORE_THRESHOLD = 55
MIN_INTERN_SCORE_THRESHOLD = 35
TIER_1_SCORE_THRESHOLD = 75

# Freshness Cutoff (Days)
MAX_POSTING_AGE_DAYS = 30
MAX_DIRECT_ATS_AGE_DAYS = 120
MAX_INTERN_AGE_DAYS = 90

# Concurrency & Anti-Monopoly Guardrails
DEFAULT_MAX_ROLES_PER_COMPANY = 3
MAX_CONCURRENT_COMPANIES = 20
DEFAULT_HARVEST_LIMIT = 1000
WORKABLE_CONCURRENCY_LIMIT = 2

# Top-Tier / High-Interest Companies to Pin
TOP_TIER_COMPANIES = {
    "zepto", "swiggy", "cred", "browserstack", "postman", "zerodha",
    "sarvam", "sarvam-ai", "krutrim", "khatabook", "modal", "perplexity",
    "stripe", "openai", "anthropic", "cloudflare", "datadog", "supabase",
    "cohere", "huggingface", "midjourney", "scale-ai", "replit", "cursor",
    "planetscale", "togetherai", "anyscale", "railway", "clickhouse", "gitlab",
    "brave", "sentry", "grafana", "canonical"
}
