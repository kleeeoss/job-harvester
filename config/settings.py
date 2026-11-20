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
    github_url: str = "https://github.com/Garv-Vaidya"
    linkedin_url: str = "https://linkedin.com/in/garv-vaidya"
    flagship_projects: List[str] = field(default_factory=lambda: [
        "Lucid-CI (Distributed containerized CI/CD runner engine in Go)",
        "Ares (High-performance network runtime)",
        "Leviathan (Cloud resource orchestrator)",
        "SyncNote (Real-time distributed notes platform)"
    ])
    core_stack: List[str] = field(default_factory=lambda: [
        "Go", "Python", "Docker", "Kubernetes", "AWS", "Linux",
        "Distributed Systems", "CI/CD Engines", "Microservices", "AI/ML Systems"
    ])

PROFILE = CandidateProfile()

# Compensation & Tier Constants
MIN_INTERN_STIPEND_INR = 10000
MAX_INTERN_STIPEND_CAP_INR = 50000

MIN_JOB_SALARY_LPA = 10.0
MAX_JOB_SALARY_CAP_LPA = 60.0

TOP_TIER_MIN_LPA = 20.0
TOP_TIER_MIN_STIPEND_INR = 30000

# Top-Tier / High-Interest Companies to Pin
TOP_TIER_COMPANIES = {
    "zepto", "swiggy", "cred", "browserstack", "postman", "zerodha",
    "sarvam", "sarvam-ai", "krutrim", "khatabook", "modal", "perplexity",
    "stripe", "openai", "anthropic", "cloudflare", "datadog", "supabase",
    "cohere", "huggingface", "midjourney", "scale-ai", "replit", "cursor"
}
