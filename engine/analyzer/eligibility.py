import re
from datetime import datetime, timezone
from typing import Tuple, Optional, Any
from .text_extractor import clean_text
from config.settings import MAX_POSTING_AGE_DAYS, MAX_INTERN_AGE_DAYS, MAX_DIRECT_ATS_AGE_DAYS

RE_RESTRICTED_CITIZENSHIP = re.compile(
    r'\b(us\s*citizen\s*only|u\.s\.\s*citizen\s*only|us\s*citizenship\s*required|'
    r'security\s*clearance\s*required|active\s*(secret|ts/sci|dod)\s*clearance|'
    r'must\s*reside\s*in\s*the\s*us|us\s*work\s*authorization\s*required|'
    r'hold\s*us\s*work\s*authorization|must\s*have\s*valid\s*us\s*work\s*authorization|'
    r'no\s*c2c|w2\s*only|us\s*or\s*green\s*card\s*holder)\b',
    re.IGNORECASE
)

RE_EXCLUDED_TITLES = re.compile(
    r'\b('
    r'sde\s*[-–—:]?\s*(?:2|ii|-2)|swe\s*[-–—:]?\s*(?:2|ii|-2)|'
    r'software\s*(?:development\s*)?engineer\s*[-–—:]?\s*(?:2|ii|-2)|'
    r'engineer\s*[-–—:]?\s*(?:2|ii|-2)|developer\s*[-–—:]?\s*(?:2|ii|-2)|'
    r'sde\s*[-–—:]?\s*(?:3|iii|-3)|swe\s*[-–—:]?\s*(?:3|iii|-3)|'
    r'software\s*(?:development\s*)?engineer\s*[-–—:]?\s*(?:3|iii|-3)|'
    r'engineer\s*[-–—:]?\s*(?:3|iii|-3)|developer\s*[-–—:]?\s*(?:3|iii|-3)|'
    r'intermediate|'
    r'field\s*engineer|'
    r'developer\s*relations|devrel|'
    r'qa\s*engineer|qa\s*automation|quality\s*assurance|'
    r'sdet|engineer\s+in\s+test|'
    r'professional\s*services?\s*engineer|technical\s*services?\s*engineer|'
    r'technical\s*account\s*(?:engineer|manager)|tae|tam'
    r')\b',
    re.IGNORECASE
)

RE_SENIOR_MANAGEMENT = re.compile(
    r'\b('
    r'senior|sr\.?|manager|management|director|vp|vice\s*president|head\s*of|chief|executive|'
    r'staff|principal|lead|architect'
    r')\b',
    re.IGNORECASE
)

RE_NON_TECH = re.compile(
    r'\b('
    r'marketing|product\s*manager|user\s*research|brand|communication|'
    r'sales|recruiter|recruiting|talent|account\s*executive|legal|finance|operations|'
    r'business\s*development|human\s*resources|hr|design(?:er|s|ing)?|product\s*designer|graphic|support|'
    r'customer\s*success|customer\s*support|accountant|alliances|partner\s*manager|account\s*manager|'
    r'program\s*manager|adoption\s*specialist|curriculum|community|strategist|strategy|evangelist|advocate|'
    r'people\s*(?:systems?|operations|ops|tech|team|experience)|business\s*systems|'
    r'it\s*(?:systems?\s*)?(?:support|helpdesk|engineer|specialist|administrator|operations|tech)|helpdesk|desktop\s*support|'
    r'sales\s*engineer|solutions?\s*engineer'
    r')\b',
    re.IGNORECASE
)

RE_ENGINEERING = re.compile(
    r'\b('
    r'software|backend|frontend|full\s*stack|systems?|infrastructure|devops|cloud|platform|sre|'
    r'site\s*reliability|distributed|data\s*engineer|data\s*scientist|'
    r'machine\s*learning|ml\s*(?:engineer|developer|infrastructure)|'
    r'ai\s*(?:engineer|developer|researcher|scientist|infrastructure|systems|compiler|model)|'
    r'kernel|compiler|runtime|mts|member\s*of\s*technical\s*staff|technical\s*staff|developer|engineer'
    r')\b',
    re.IGNORECASE
)

RE_SENIOR_EXPERIENCE = re.compile(
    r'(\b(?:requires?|minimum|min|at\s*least|with|have)\s*(?:of\s*)?(?:[3-9]|1[0-9])\+?\s*years?(?:\s*of)?(?:\s+[a-z-]+){0,3}\s+experience\b)|'
    r'(\b(?:[3-9]|1[0-9])\+?\s*years?(?:\s*of)?(?:\s+[a-z-]+){0,3}\s+experience\s*(?:required|needed|preferred|mandatory)?\b)',
    re.IGNORECASE
)

RE_CGPA_CUTOFF = re.compile(
    r'(\b(minimum|min|at\s*least|requires?)\s*(?:of\s*)?(8\.[0-9]|9\.[0-9]|[89][0-9]%)\s*(gpa|cgpa|cutoff|aggregate|marks)?\b)|'
    r'(\b(8\.[0-9]|9\.[0-9]|[89][0-9]%)\s*(gpa|cgpa|cutoff|minimum|min|above|aggregate)\b)',
    re.IGNORECASE
)

def is_engineering_role(title: str) -> bool:
    """
    Evaluates whether a role title belongs to core engineering accessible to the candidate profile:
    - Rejects non-tech titles (marketing, sales, HR, legal, finance, design, user research, etc.)
    - Rejects excluded seniority & mid-levels (SDE2, SDE-2, SDE II, Engineer II, Intermediate)
    - Rejects senior management (Senior, Staff, Principal, Lead, Architect, Manager, Director, VP)
    - Rejects Field Engineer, DevRel, QA, TAM
    - Accepts early career engineering and engineering internships
    """
    if not title:
        return False
    title_clean = title.strip()
    is_intern = bool(re.search(r'\b(intern|internship|co-op|trainee)\b', title_clean, re.I))

    # 1. Hard-excluded titles (SDE2, Field Engineer, DevRel, QA, TAM) apply to both intern and full-time
    if RE_EXCLUDED_TITLES.search(title_clean):
        return False

    # 2. Seniority filtering
    if not is_intern:
        is_mts = bool(re.search(r'\bmember\s*of\s*technical\s*staff\b', title_clean, re.I))
        if not is_mts:
            if RE_SENIOR_MANAGEMENT.search(title_clean):
                return False
        else:
            if re.search(r'\b(senior|sr\.?|lead|principal|director|manager)\b|(?<!technical\s)\bstaff\b', title_clean, re.I):
                return False

    # 3. Non-technical roles
    if RE_NON_TECH.search(title_clean):
        return False

    # 4. Require positive engineering indicator
    if is_intern:
        return bool(RE_ENGINEERING.search(title_clean)) or bool(re.search(r'\b(tech|engineer|developer|coding|systems)\b', title_clean, re.I))

    return bool(RE_ENGINEERING.search(title_clean))

def parse_posting_date(date_val: Any) -> Optional[datetime]:
    """Parses diverse date formats (ISO string, epoch seconds/ms, YYYY-MM-DD)."""
    if not date_val:
        return None
    if isinstance(date_val, (int, float)):
        # Epoch seconds or milliseconds
        ts = date_val / 1000.0 if date_val > 1e11 else date_val
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(date_val, str):
        date_str = date_val.strip()
        if date_str.isdigit():
            val = int(date_str)
            ts = val / 1000.0 if val > 1e11 else float(val)
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                return None
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
    return None

def is_posting_fresh(posted_date: Any, max_days: int = MAX_POSTING_AGE_DAYS) -> Tuple[bool, str]:
    """Enforces freshness cutoff when creation/published timestamp is available."""
    dt = parse_posting_date(posted_date)
    if not dt:
        return True, "Fresh (no timestamp provided)"
    now = datetime.now(timezone.utc)
    age_days = (now - dt).total_seconds() / 86400.0
    if age_days > max_days:
        return False, f"Stale posting: {int(age_days)} days old (exceeds {max_days}-day cutoff)"
    return True, f"Fresh ({int(age_days)} days old)"

def has_cgpa_cutoff(job_text: str) -> bool:
    """Detects whether a job states an 8.0+ CGPA requirement (for -5 soft penalty)."""
    return bool(RE_CGPA_CUTOFF.search(clean_text(job_text)))

def check_eligibility(
    job_text: str,
    is_internship: bool = False,
    role_title: str = "",
    posted_date: Any = None,
    is_direct_ats: bool = False
) -> Tuple[bool, str]:
    """
    Examines requisition text against hard disqualifiers:
    1. US citizenship / security clearance / US-only residency.
    2. Hard seniority and role filtering: Senior, Staff, Lead, Manager, SDE2, Field Eng, DevRel, QA.
    3. Freshness cutoff: 90 days for internships, 120 days for verified direct ATS roles, 30 days for raw feed links.
    4. 3+ years experience.
    """
    text = clean_text(job_text).lower()

    # 1. Reject citizenship / security clearance / US-only residency
    if RE_RESTRICTED_CITIZENSHIP.search(text):
        return False, "US/EU citizenship or security clearance required"

    # 2. Hard Seniority & Role Filtering
    if role_title:
        if not is_engineering_role(role_title):
            return False, f"Senior/Lead or excluded role rejected for undergraduate profile ({role_title})"

    # 3. Reject excessive experience (3+ years mandatory)
    if not is_internship and RE_SENIOR_EXPERIENCE.search(text):
        return False, "Excessive experience required (3+ years mandatory)"

    # 4. Freshness cutoff
    if posted_date:
        max_days = MAX_INTERN_AGE_DAYS if is_internship else (MAX_DIRECT_ATS_AGE_DAYS if is_direct_ats else MAX_POSTING_AGE_DAYS)
        fresh, reason = is_posting_fresh(posted_date, max_days=max_days)
        if not fresh:
            return False, reason

    return True, "Eligible"
