from typing import List
from config.settings import PROFILE

def generate_cold_pitch(company: str, role_title: str, tech_stack: List[str] = None) -> str:
    """
    Generates a concise ~75-word founder cold outreach message for Garv Vaidya.
    Directly references relevant flagship systems projects and live portfolio.
    """
    tech_str = ", ".join(tech_stack[:3]) if tech_stack else "Go and distributed infrastructure"
    
    pitch = (
        f"Hi team {company},\n\n"
        f"I came across the {role_title} opening. I'm Garv Vaidya, a systems and backend engineer "
        f"(B.Tech CSE '27) specializing in {tech_str}. "
        f"I built Lucid-CI, a containerized distributed CI/CD runner engine handling isolated execution pipelines, "
        f"and Ares, a high-throughput network engine. "
        f"I'd love to bring this systems focus to {company}. "
        f"You can review my live portfolio and architecture breakdowns at https://garvvaidya.vercel.app.\n\n"
        f"Best regards,\nGarv Vaidya"
    )
    return pitch
