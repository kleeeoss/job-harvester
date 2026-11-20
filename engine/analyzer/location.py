import re
from typing import Tuple
from .text_extractor import clean_text

RE_INDIA_LOCATIONS = re.compile(
    r'\b(india|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|delhi\s*ncr|ncr|'
    r'noida|gurgaon|gurugram|chennai|kolkata|ahmedabad|jabalpur|jaipur|'
    r'karnataka|telangana|maharashtra|tamil\s*nadu|haryana|uttar\s*pradesh|kerala)\b',
    re.IGNORECASE
)

RE_RESTRICTED_REMOTE = re.compile(
    r'(?:\bu\.s\.?(?!\w)\s*(?:only|remote)|\bus\s*only|\busa\s*only|\b('
    r'remote\s*[-–—(]\s*(?:us|usa|u\.s\.?|united\s*states|north\s*america|emea|latam|uk|canada|europe)\s*(?:only|\))|'
    r'united\s*states\s*only|'
    r'open\s*only\s*to\s*(?:us|candidates\s*in\s*the\s*us|candidates\s*located\s*within\s*the\s*(?:continental\s*)?united\s*states)|'
    r'must\s*(?:reside|be\s*located)\s*in\s*the\s*(?:us|united\s*states))\b)',
    re.IGNORECASE
)

RE_FOREIGN_GEO_RESTRICTED = re.compile(
    r'(?:\bu\.s\.?(?!\w)|\bus\b|\busa\b|\b('
    r'united\s*states|amer|americas|latam|emea|europe|north\s*america|'
    r'uk|united\s*kingdom|canada|germany|france|australia|singapore|ireland|netherlands|'
    r'sweden|new\s*york|san\s*francisco|bay\s*area|california|ca|ny|tx|texas|wa|washington|'
    r'belgrade|london|boston|chicago|austin|seattle|dublin|palo\s*alto|philadelphia)\b)',
    re.IGNORECASE
)

def check_location(location_str: str, job_text: str = "") -> Tuple[bool, str, str]:
    """
    Evaluates candidate geographic eligibility:
    - Candidate: Garv Vaidya, India resident, no passport currently.
    - India roles: Both Remote AND On-site are acceptable.
    - Foreign roles: MUST BE strictly 100% Fully Remote (Worldwide/Global).
    Returns: (is_valid, location_type, reason)
    """
    loc_clean = clean_text(location_str).lower().strip()
    text_clean = clean_text(job_text[:1000]).lower()

    # 1. Determine if location is in India
    is_india = bool(RE_INDIA_LOCATIONS.search(loc_clean))
    if not is_india and loc_clean in ["remote", "", "anywhere"]:
        is_india = bool(RE_INDIA_LOCATIONS.search(text_clean))

    is_hybrid = bool(re.search(r'\bhybrid\b', loc_clean) or re.search(r'\bhybrid\b', text_clean))
    is_remote = bool(re.search(r'\b(remote|work\s*from\s*home|wfh|anywhere|worldwide)\b', loc_clean))

    if is_india:
        loc_type = "India (Remote)" if (is_remote and not is_hybrid) else "India (On-site/Hybrid)"
        return True, loc_type, "Eligible (India remote or on-site permitted)"

    # 2. Foreign Roles: Must be strictly 100% Fully Remote
    # If the location string is a physical foreign city/country without 'remote', it is Foreign On-Site
    if not is_remote:
        return False, "Foreign On-Site", "Foreign on-site role rejected: Candidate lacks foreign passport/work authorization"

    # Reject foreign hybrid roles (cannot commute abroad)
    if is_hybrid:
        return False, "Foreign Hybrid", "Foreign hybrid role rejected: Candidate lacks foreign passport/work authorization"

    # Reject explicitly restricted remote positions (US-only, etc.)
    if RE_RESTRICTED_REMOTE.search(loc_clean) or RE_RESTRICTED_REMOTE.search(text_clean):
        return False, "Restricted Foreign Remote", "Remote position restricted to US/foreign residents only"

    # Reject foreign geo-fenced remotes (e.g. North America (Remote), Europe (Remote)) unless explicitly global
    is_explicit_global = any(k in loc_clean for k in ["global", "worldwide", "anywhere", "all locations"])
    if RE_FOREIGN_GEO_RESTRICTED.search(loc_clean) and not is_explicit_global:
        return False, "Restricted Foreign Remote", "Remote position restricted to foreign region (North America/Europe/US)"

    return True, "Worldwide Remote", "Eligible (100% Global Remote)"
