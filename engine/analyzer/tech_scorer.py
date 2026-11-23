import re
from typing import List, Tuple, Dict, Any
from .text_extractor import clean_text
from .eligibility import has_cgpa_cutoff
from config.settings import TOP_TIER_COMPANIES, TIER_1_SCORE_THRESHOLD

# Flagship Stack Vectors (Max 40 points total)
RE_GO_CASE_SENSITIVE = re.compile(
    r'(?:'
    r'(?:\b(?:in|with|using|of|for|experience\s+with|proficient\s+(?:in|with)|knowledge\s+of|background\s+in|written\s+in|written\s+using)\s+Go\b)|'
    r'(?:\bGo\s*[,/;)]\b)|'
    r'(?:[/(]\s*Go\b)|'
    r'(?:\bGo\s*/)|'
    r'(?:\b(?:stack|skills?|technologies|languages?)\s*:[^.\n]*?\bGo\b)|'
    r'(?:\b(?:python|docker|kubernetes|k8s|c\+\+|rust|aws|linux)\s+(?:and|or|,)\s+Go\b)|'
    r'(?:\bGo\s+(?:and|or)\s+(?:python|docker|kubernetes|k8s|c\+\+|rust|aws|linux)\b)|'
    r'(?:\bGo\s+(?:language|code|runtime|routines|backend|microservices|developer|engineer|programming|lang|systems|infra(?:structure)?)\b)'
    r')'
)
RE_GOLANG_CASE_INSENSITIVE = re.compile(r'\b(?:golang|go\s+(?:developer|engineer|programming|runtime|backend|microservices|code|routines|lang))\b', re.I)

STACK_VECTORS = [
    ("Go / Golang", 12, []),  # Checked via RE_GOLANG_CASE_INSENSITIVE and RE_GO_CASE_SENSITIVE
    ("Python", 8, [r'\bpython\b', r'\bpython3\b']),
    ("FastAPI", 6, [r'\bfastapi\b', r'\basyncio\b', r'\buvicorn\b']),
    ("Docker / Containers / gVisor", 8, [r'\bdocker\b', r'\bgvisor\b', r'\bcontainers?\b', r'\bcontainerized\b', r'\bcontainer\s*isolation\b']),
    ("Kubernetes / K8s", 8, [r'\bkubernetes\b', r'\bk8s\b', r'\bhelm\b']),
    ("AWS / Cloud Infrastructure", 6, [r'\baws\b', r'\bamazon\s*web\s*services\b', r'\bcloud\s*infrastructure\b', r'\bgcp\b']),
    ("Terraform / IaC", 6, [r'\bterraform\b', r'\biac\b', r'\binfrastructure\s*as\s*code\b', r'\bpulumi\b']),
    ("Distributed Systems", 8, [r'\bdistributed\s*systems?\b', r'\bconcurrency\b', r'\bgrpc\b', r'\bhigh\s*throughput\b', r'\braft\b', r'\bconsensus\b']),
    ("Linux / Systems Programming", 8, [r'\blinux\b', r'\bos\s*internals\b', r'\bkernel\b', r'\bsystems?\s*programming\b', r'\blow[- ]level\b']),
    ("CI/CD Engines / DevOps", 8, [r'\bci/cd\b', r'\bpipeline\b', r'\bbuild\s*system\b', r'\brunner\b', r'\bdevops\b', r'\bgithub\s*actions\b']),
    ("DevSecOps / AST Sandbox", 6, [r'\bdevsecops\b', r'\bsandbox(?:ing)?\b', r'\bast\b', r'\bsecurity\s*analysis\b', r'\bvulnerability\b']),
    ("Vertex AI / LLM / AI Agents", 8, [r'\bvertex\s*ai\b', r'\bgemini\b', r'\bllm\b', r'\bai\s*agents?\b', r'\brag\b', r'\bvector\s*db\b', r'\bmodel\s*serving\b'])
]

ROLE_FOCUS_WEIGHTS = [
    (25, [r'\bsystems?\s*engineer\b', r'\binfrastructure\s*engineer\b', r'\bcloud\s*engineer\b', r'\bplatform\s*engineer\b', r'\bkernel\s*engineer\b']),
    (25, [
        r'\b(?:software(?:\s*(?:engineer(?:ing)?|developer|development))?|systems?(?:\s*engineer(?:ing)?)?|cloud(?:\s*engineer(?:ing)?)?|backend(?:\s*engineer(?:ing)?)?|frontend(?:\s*engineer(?:ing)?)?|full\s*stack(?:\s*engineer(?:ing)?)?|devops(?:\s*engineer(?:ing)?)?|platform(?:\s*engineer(?:ing)?)?|infrastructure(?:\s*engineer(?:ing)?)?|ai(?:\s*engineer(?:ing)?)?|ml(?:\s*engineer(?:ing)?)?|machine\s*learning(?:\s*engineer(?:ing)?)?|data(?:\s*engineer(?:ing)?)?)\s*(?:engineering\s*)?intern(?:ship)?\b',
        r'\bintern(?:ship)?\s*[-–—:]\s*(?:software|systems?|backend|cloud|ai|platform|infrastructure|full\s*stack)\b',
        r'\bengineering\s*intern(?:ship)?\b',
    ]),
    (22, [r'\bbackend\s*(?:software\s*)?engineer\b', r'\bdistributed\s*systems?\s*engineer\b']),
    (20, [r'\bsre\b', r'\bsite\s*reliability\s*engineer\b', r'\bdevops\s*engineer\b', r'\bml\s*ops\b', r'\bai\s*infrastructure\b']),
    (18, [r'\bmember\s*of\s*technical\s*staff\b', r'\bmts\b', r'\bsoftware\s*(?:development\s*)?engineer\b', r'\bsoftware\s*engineer\b']),
    (14, [r'\bfull\s*stack\b', r'\bdeveloper\b', r'\bengineer\b'])
]

def score_job_requisition(
    title: str,
    job_text: str,
    company: str,
    location_type: str,
    is_internship: bool,
    pay_tier_val: str,
    geo_boost: int = 15,
    contact_email: str = None
) -> Tuple[int, bool, Dict[str, Any], str]:
    """
    Computes a comprehensive 0–100 score:
    - Tech Stack Fit (Max 40)
    - Role Focus Fit (Max 25)
    - Geographic & Work Auth Alignment (Max 20)
    - Compensation & Founder Outreach Multiplier (Max 15)
    - Soft Penalties (-5 for 8+ CGPA cutoff, -10 for UI-only frontend)
    Returns: (total_score, is_tier_1, score_breakdown, match_rationale)
    """
    raw_combined = f"{title} {job_text}"
    combined = raw_combined.lower()
    clean_title = clean_text(title).lower()

    # 1. Tech Stack Fit (Max 40)
    stack_points = 0
    matched_skills = []
    for skill_name, points, patterns in STACK_VECTORS:
        matched = False
        if skill_name == "Go / Golang":
            if RE_GOLANG_CASE_INSENSITIVE.search(combined) or RE_GO_CASE_SENSITIVE.search(raw_combined):
                matched = True
        else:
            if any(re.search(pat, combined, re.I) for pat in patterns):
                matched = True

        if matched:
            stack_points += points
            matched_skills.append(skill_name)
    stack_points = min(stack_points, 40)

    # 2. Role Focus Fit (Max 25)
    role_points = 14  # baseline
    for pts, patterns in ROLE_FOCUS_WEIGHTS:
        if any(re.search(pat, clean_title, re.I) for pat in patterns):
            role_points = pts
            break

    # 3. Geographic Alignment (Max 20)
    geo_points = min(geo_boost, 20)

    # 4. Compensation & Prestige Multiplier (Max 15)
    prestige_points = 0
    comp_clean = company.lower().strip()
    if comp_clean in TOP_TIER_COMPANIES or any(t in comp_clean for t in ["sarvam", "modal", "supabase", "stripe", "perplexity", "cursor"]):
        prestige_points += 10
    elif any(k in comp_clean for k in ["gitlab", "railway", "planetscale", "clickhouse", "razorpay"]):
        prestige_points += 6

    # Founder cold email bonus
    if contact_email or "DIRECT_FOUNDER_EMAIL" in pay_tier_val:
        prestige_points += 5

    # High comp bonus
    if any(h in pay_tier_val for h in ["30 – 45", "45 – 60", "30,000 – ₹40,000", "40,000 – ₹50,000"]):
        prestige_points += 5
    elif any(m in pay_tier_val for m in ["15 – 30", "20,000 – ₹30,000"]):
        prestige_points += 3

    prestige_points = min(prestige_points, 15)

    # 5. Soft Penalties
    penalties = 0
    penalty_notes = []

    # Soft penalty: -5 for 8.0+ CGPA requirement (instead of hard drop)
    if has_cgpa_cutoff(job_text):
        penalties += 5
        penalty_notes.append("-5 for 8.0+ CGPA stated")

    # Soft penalty: -10 if title is strictly Frontend / UI with no systems mention
    if bool(re.search(r'\b(frontend|react|ui/ux)\b', clean_title)) and not any(k in clean_title for k in ["systems", "backend", "full stack"]):
        penalties += 10
        penalty_notes.append("-10 for Frontend-only title")

    total_score = max(0, min(100, (stack_points + role_points + geo_points + prestige_points) - penalties))
    is_tier_1 = (total_score >= TIER_1_SCORE_THRESHOLD)

    breakdown = {
        "stack_points": stack_points,
        "role_points": role_points,
        "geo_points": geo_points,
        "prestige_points": prestige_points,
        "penalties": penalties,
        "penalty_notes": penalty_notes,
        "matched_skills": matched_skills[:5]
    }

    rationale = ", ".join(matched_skills[:4]) if matched_skills else "Systems & Backend Engineering"

    return total_score, is_tier_1, breakdown, rationale

def score_tech_stack(title: str, job_text: str) -> Tuple[int, List[str], str]:
    """Backward-compatible helper returning (score, matched_skills, rationale)."""
    score, _, breakdown, rationale = score_job_requisition(
        title=title,
        job_text=job_text,
        company="Tech Company",
        location_type="Remote",
        is_internship=False,
        pay_tier_val="[Unlisted Salary]"
    )
    return score, breakdown.get("matched_skills", []), rationale

