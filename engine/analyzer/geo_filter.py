import re
from typing import Tuple
from .text_extractor import clean_text

RE_INDIA_LOCATIONS = re.compile(
    r'\b(india|bengaluru|bangalore|hyderabad|pune|mumbai|delhi|delhi\s*ncr|ncr|'
    r'noida|gurgaon|gurugram|chennai|kolkata|ahmedabad|jabalpur|jaipur|'
    r'karnataka|telangana|maharashtra|tamil\s*nadu|haryana|uttar\s*pradesh|kerala)\b',
    re.IGNORECASE
)

RE_REMOTE_IN_CASE_SENSITIVE = re.compile(
    r'(?:\b(?:Remote|REMOTE)\s*[,/–—-]\s*IN\b|\bIN\s*[,/–—-]\s*(?:Remote|REMOTE)\b)'
)

RE_GLOBAL_REMOTE = re.compile(
    r'\b(worldwide|global|anywhere|all\s*locations|work\s*from\s*anywhere|'
    r'async\s*remote|apac\s*remote|remote\s*[-–—(]\s*apac|remote\s*-\s*global|remote\s*-\s*worldwide)\b',
    re.IGNORECASE
)

RE_US_HARD_DROP = re.compile(
    r'(?:\b(?:u\.s\.?|us|usa)\s*[- ]?\s*(?:only|based|residents?|citizens?)\b|\b('
    r'united\s*states\s*only|us/canada\s*only|us\s*&\s*canada\s*only|north\s*america\s*only|'
    r'must\s*reside\s*in\s*(?:the\s*)?(?:us|united\s*states)|'
    r'open\s*only\s*to\s*(?:us|candidates\s*in\s*the\s*us)|'
    r'must\s*be\s*legally\s*authorized\s*to\s*work\s*in\s*the\s*us\s*without\s*sponsorship|'
    r'w2\s*only|no\s*c2c)\b)',
    re.IGNORECASE
)

RE_FOREIGN_RESTRICTIONS = re.compile(
    r'(?:\b(?:eea|eu\s*only|emea(?:\s*only)?|uk\s*only|latam(?:\s*only)?|canada\s*only|australia\s*only|'
    r'united\s*states\s*only|us\s*only|usa\s*only|u\.s\.\s*only|us/canada\s*only|us\s*&\s*canada\s*only|north\s*america\s*only|americas?\s*only|'
    r'europe\s*only)\b|'
    r'\bremote\s*[-–—(]\s*(?:eea|eu|emea|latam|uk|canada|europe|north\s*america|americas?|middle\s*east)\b|'
    r'\b(?:remote\s*\(eea\)|remote\s*\(eu\s*only\)|remote\s*\(emea\)|remote\s*\(uk\))\b|'
    r'\b(?:must\s*(?:reside|be\s*located|live)\s*in\s*(?:the\s*)?(?:us|united\s*states|canada|europe|uk|north\s*america|americas?|latin\s*america|eea|eu|emea))\b|'
    r'\b(?:authorized\s*to\s*work\s*in\s*(?:the\s*)?(?:us|united\s*states|canada|uk|europe|eea))\b|'
    r'\b(?:w2\s*only|no\s*c2c|must\s*be\s*legally\s*authorized\s*to\s*work\s*in\s*the\s*us\s*without\s*sponsorship)\b)',
    re.IGNORECASE
)

RE_FOREIGN_GEO_RESTRICTED = re.compile(
    r'(?:\bu\.s\.?(?!\w)|\bus\b|\busa\b|\b('
    r'united\s*states|amer|americas|latam|latin\s*america|emea|europe|north\s*america|middle\s*east|'
    r'uk|united\s*kingdom|great\s*britain|england|scotland|wales|canada|germany|france|australia|new\s*zealand|'
    r'singapore|ireland|netherlands|sweden|switzerland|poland|spain|italy|brazil|mexico|'
    r'colombia|argentina|chile|peru|uruguay|venezuela|nigeria|kenya|south\s*africa|egypt|ghana|'
    r'pakistan|bangladesh|philippines|indonesia|vietnam|thailand|malaysia|'
    r'japan|korea|taiwan|israel|ksa|saudi(?:\s*arabia)?|uae|dubai|czech(?:ia)?|estonia|finland|norway|denmark|'
    r'turkey|qatar|bahrain|kuwait|greece|austria|belgium|hungary|romania|bulgaria|croatia|'
    r'portugal|lithuania|latvia|slovakia|slovenia|cyprus|malta|luxembourg|iceland|serbia|'
    r'alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|'
    r'hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|'
    r'michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new\s*hampshire|new\s*jersey|'
    r'new\s*mexico|new\s*york|north\s*carolina|north\s*dakota|ohio|oklahoma|oregon|pennsylvania|'
    r'rhode\s*island|south\s*carolina|south\s*dakota|tennessee|texas|utah|vermont|virginia|washington|'
    r'west\s*virginia|wisconsin|wyoming|'
    r'orlando|cincinnati|columbus|cleveland|tampa|miami|atlanta|austin|dallas|houston|san\s*antonio|'
    r'chicago|boston|cambridge|denver|boulder|pittsburgh|philadelphia|seattle|bellevue|redmond|'
    r'portland|san\s*francisco|san\s*mateo|san\s*jose|palo\s*alto|mountain\s*view|sunnyvale|'
    r'santa\s*clara|cupertino|los\s*angeles|san\s*diego|bay\s*area|nyc|new\s*york\s*city|'
    r'madrid|barcelona|valencia|paris|lyon|berlin|munich|frankfurt|amsterdam|rotterdam|'
    r'london|manchester|birmingham|edinburgh|bristol|dublin|belfast|warsaw|krakow|prague|'
    r'brno|budapest|bucharest|sofia|belgrade|zagreb|athens|rome|milan|zurich|geneva|vienna|'
    r'stockholm|gothenburg|oslo|copenhagen|helsinki|espoo|tampere|tallinn|riga|vilnius|'
    r'lisbon|porto|'
    r'ontario|quebec|british\s*columbia|alberta|manitoba|saskatchewan|nova\s*scotia|new\s*brunswick|'
    r'toronto|vancouver|montreal|ottawa|calgary|waterloo|sydney|melbourne|brisbane|auckland|'
    r'tokyo|seoul|taipei|tel\s*aviv|sao\s*paulo|rio|buenos\s*aires|mexico\s*city|bogota)\b|'
    r'(?:,\s*|[-–—/]\s*)\b(?:al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy|dc)\b)',
    re.IGNORECASE
)

RE_HYBRID_IN_TEXT = re.compile(
    r'\bhybrid\s*(?:work|role|schedule|model|arrangement|environment|setup|policy|days|in-office|office)\b',
    re.IGNORECASE
)

RE_VISA_SPONSORSHIP_BOOST = re.compile(
    r'\b(visa\s*sponsorship\s*provided|we\s*sponsor\s*visas?|sponsorship\s*available|open\s*to\s*international\s*applicants?)\b',
    re.IGNORECASE
)

def evaluate_geo_and_auth(
    location_str: str,
    job_text: str = "",
    is_internship: bool = False
) -> Tuple[bool, str, str, int]:
    """
    Evaluates geographic eligibility and work authorization.
    Returns: (is_eligible, location_type, reason, geo_boost_points)

    Consolidated Rules:
    - Structured location immunity: If location explicitly contains India or Worldwide/Global Remote,
      boilerplate US legal footers ('cannot sponsor visas') DO NOT cause a hard-drop.
    - Bare 'hybrid' in job_text is ignored (to protect 100% remote jobs mentioning 'hybrid cloud' or 'hybrid search').
      Explicit 'hybrid work/role/schedule/model' is checked in text.
    - Explicitly rejects EEA, EU only, EMEA only, UK only, LATAM only, and regional remotes.
    - Internships: strictly 100% remote. Full-time: India on-site or remote, foreign strictly 100% remote.
    """
    loc_clean = clean_text(location_str).lower().strip()
    text_clean = clean_text(job_text[:1200]).lower()

    # 1. Detect India presence
    is_india = bool(RE_INDIA_LOCATIONS.search(loc_clean)) or bool(RE_REMOTE_IN_CASE_SENSITIVE.search(location_str))
    if not is_india and loc_clean in ["remote", "", "anywhere", "worldwide"]:
        is_india = bool(re.search(
            r'\b(bengaluru|bangalore|hyderabad|pune|mumbai|delhi|delhi\s*ncr|ncr|noida|gurgaon|gurugram|chennai|kolkata|ahmedabad|jabalpur)\b|'
            r'\b(?:based|located|work|office|position)\s*(?:in|at)\s*india\b',
            text_clean
        ))

    is_remote = bool(re.search(r'\b(remote|work\s*from\s*home|wfh|anywhere|worldwide)\b', loc_clean))
    is_hybrid = bool(re.search(r'\bhybrid\b', loc_clean) or RE_HYBRID_IN_TEXT.search(text_clean))
    is_global_remote = bool(RE_GLOBAL_REMOTE.search(loc_clean)) or (
        is_remote and not is_india and not RE_US_HARD_DROP.search(loc_clean) and
        not RE_FOREIGN_RESTRICTIONS.search(loc_clean) and
        any(w in loc_clean for w in ["anywhere", "global", "worldwide"])
    )

    sponsorship_bonus = 5 if RE_VISA_SPONSORSHIP_BOOST.search(text_clean) else 0

    # 2. Process India Roles
    if is_india:
        loc_type = "India (Remote)" if (is_remote and not is_hybrid) else "India (On-site/Hybrid)"
        if is_internship and loc_type != "India (Remote)":
            return False, loc_type, "Internship rejected: Must be strictly 100% remote", 0
        points = 18 if loc_type == "India (Remote)" else 15
        return True, loc_type, "Eligible India position", points + sponsorship_bonus

    # 3. Check Hard Drops for US/EEA/EU/UK/LATAM/Regional Restrictions
    if RE_FOREIGN_RESTRICTIONS.search(loc_clean) or RE_FOREIGN_RESTRICTIONS.search(text_clean):
        return False, "Foreign Restricted", f"Position strictly restricted to foreign region / work authorization ({location_str.strip()})", 0

    if RE_US_HARD_DROP.search(loc_clean) or RE_US_HARD_DROP.search(text_clean):
        return False, "US Restricted", "Position strictly restricted to US residents / work authorization", 0

    # 4. Process Global / Worldwide Remote
    if is_global_remote:
        return True, "Worldwide Remote", "Eligible 100% Global Remote", 20 + sponsorship_bonus

    # 5. Check Non-Remote / Hybrid
    if not is_remote:
        return False, "Foreign On-Site", "Foreign on-site role rejected: Candidate lacks foreign visa/passport", 0

    if is_hybrid:
        return False, "Foreign Hybrid", "Foreign hybrid role rejected: Candidate lacks foreign visa/passport", 0

    # 6. Check Specific Country/City Remote Restrictions
    if RE_FOREIGN_GEO_RESTRICTED.search(loc_clean):
        return False, "Restricted Foreign Remote", f"Remote position restricted to foreign jurisdiction ({location_str.strip()})", 0

    # 7. Unrestricted Remote
    return True, "Worldwide Remote", "Eligible Unrestricted Remote", 20 + sponsorship_bonus

def check_location(location_str: str, job_text: str = "", is_internship: bool = False) -> Tuple[bool, str, str]:
    """Backward-compatible wrapper returning (is_valid, location_type, reason)."""
    valid, loc_type, reason, _ = evaluate_geo_and_auth(location_str, job_text, is_internship)
    return valid, loc_type, reason
