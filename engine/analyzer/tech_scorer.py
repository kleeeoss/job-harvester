import re
from typing import List, Tuple
from .text_extractor import clean_text

TECH_KEYWORDS = {
    "Go": [r'\bgolang\b', r'\bgo\b', r'\bgo\s*developer\b'],
    "Python": [r'\bpython\b', r'\bpython3\b', r'\bfastapi\b'],
    "Docker / Containers": [r'\bdocker\b', r'\bcontainers?\b', r'\bcontainerized\b', r'\bgvisor\b'],
    "Kubernetes": [r'\bkubernetes\b', r'\bk8s\b'],
    "AWS / Cloud": [r'\baws\b', r'\bamazon\s*web\s*services\b', r'\bcloud\b', r'\bgcp\b'],
    "Distributed Systems": [r'\bdistributed\s*systems?\b', r'\bconcurrency\b', r'\bgrpc\b', r'\bhigh\s*throughput\b'],
    "CI/CD & DevOps": [r'\bci/cd\b', r'\bpipeline\b', r'\bdevops\b', r'\brunner\b'],
    "Linux / Systems": [r'\blinux\b', r'\bsystems?\s*engineering\b', r'\bos\s*internals\b', r'\bkernel\b'],
    "AI / ML Infrastructure": [r'\bllm\b', r'\binference\b', r'\bvector\b', r'\bai\s*infrastructure\b', r'\bdeep\s*learning\b']
}

def score_tech_stack(title: str, job_text: str) -> Tuple[int, List[str], str]:
    """
    Evaluates stack alignment with Garv Vaidya's systems/cloud/backend profile.
    Returns: (score, matched_keywords, match_rationale)
    """
    clean_desc = clean_text(job_text).lower()
    clean_title = clean_text(title).lower()
    combined = f"{clean_title} {clean_desc}"

    matched = []
    for tech_name, patterns in TECH_KEYWORDS.items():
        if any(re.search(pat, combined, re.I) for pat in patterns):
            matched.append(tech_name)

    # Base score on keyword hits
    score = min(len(matched) * 15, 90)

    # Bonus if title explicitly targets Systems, Backend, Infrastructure, Platform, or DevOps
    if any(k in clean_title for k in ["systems", "backend", "infrastructure", "platform", "cloud", "devops", "software engineer", "intern"]):
        score += 10

    score = min(score, 100)
    match_rationale = ", ".join(matched[:4]) if matched else "Backend Engineering"

    return score, matched, match_rationale
