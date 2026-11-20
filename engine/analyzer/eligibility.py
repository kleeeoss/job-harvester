import re
from typing import Tuple
from .text_extractor import clean_text

RE_RESTRICTED_CITIZENSHIP = re.compile(
    r'\b(us\s*citizen\s*only|u\.s\.\s*citizen\s*only|us\s*citizenship\s*required|'
    r'security\s*clearance\s*required|active\s*(secret|ts/sci|dod)\s*clearance|'
    r'must\s*reside\s*in\s*the\s*us|us\s*work\s*authorization\s*required|'
    r'hold\s*us\s*work\s*authorization|must\s*have\s*valid\s*us\s*work\s*authorization|'
    r'no\s*c2c|w2\s*only|us\s*or\s*green\s*card\s*holder)\b',
    re.IGNORECASE
)

RE_HIGH_GPA_CUTOFF = re.compile(
    r'(\b(minimum|min|at\s*least|requires?)\s*(?:of\s*)?(8\.[0-9]|9\.[0-9]|[89][0-9]%)\s*(gpa|cgpa|cutoff|aggregate|marks)?\b)|'
    r'(\b(8\.[0-9]|9\.[0-9]|[89][0-9]%)\s*(gpa|cgpa|cutoff|minimum|min|above|aggregate)\b)',
    re.IGNORECASE
)

RE_STRICT_PAST_BATCH = re.compile(
    r'\b(2023|2024|2025)\s*(batch|graduates?|passouts?|only)\b|\b(final\s*year\s*students?\s*(?:only|ready\s*to\s*join))\b',
    re.IGNORECASE
)

RE_ELIGIBLE_BATCH = re.compile(
    r'\b(2026|2027|2028|pre-final|penultimate|3rd\s*year|third\s*year|undergraduate|b\.?tech)\b',
    re.IGNORECASE
)

def check_eligibility(job_text: str, is_internship: bool = False) -> Tuple[bool, str]:
    """
    Examines the job description text against candidate invariants:
    - Candidate: Garv Vaidya, B.Tech CSE Class of 2027, CGPA 7.17, India resident.
    """
    text = clean_text(job_text).lower()

    # 1. Reject citizenship / security clearance / US-only residency
    if RE_RESTRICTED_CITIZENSHIP.search(text):
        return False, "US/EU citizenship or security clearance required"

    # 2. Reject mandatory high GPA cutoffs (candidate has 7.17)
    if RE_HIGH_GPA_CUTOFF.search(text):
        return False, "High CGPA cutoff stated (8.0+ / 80%+ mandatory)"

    # 3. For internships, check graduation batch
    if is_internship:
        if RE_STRICT_PAST_BATCH.search(text) and not RE_ELIGIBLE_BATCH.search(text):
            return False, "Restricted to 2024/2025 batch only (not open to 2027)"

    return True, "Eligible"
