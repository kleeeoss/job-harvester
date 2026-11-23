import re
from typing import Tuple
from urllib.parse import urlparse
import httpx

RE_CAREER_HOMEPAGE_PATHS = re.compile(
    r'^(?:/(?:en|us|in|global|careers|jobs))?/(?:careers|jobs)/?$',
    re.IGNORECASE
)

CLOSED_INDICATORS = [
    "this position has been filled",
    "no longer accepting applications",
    "job is no longer available",
    "posting has expired",
    "requisition closed",
    "position closed",
    "this job has expired",
    "role is no longer open",
    "page not found",
    "job not found"
]

APPLY_TRIGGERS = [
    "apply",
    "submit application",
    "first_name",
    "first name",
    "resume",
    "cv",
    "attach resume",
    "application form",
    "submit"
]

KNOWN_ATS_DOMAINS = [
    "ashbyhq.com",
    "greenhouse.io",
    "lever.co",
    "myworkdayjobs.com",
    "workable.com",
    "rippling.com",
    "smartrecruiters.com",
    "personio.de",
    "personio.com",
    "recruitee.com",
    "gem.com"
]

def is_career_homepage(url: str) -> bool:
    """
    Enforces RULE[user_global]:
    Detects top-level career homepages (e.g. company.com/careers, amazon.jobs, boards.greenhouse.io/company).
    Returns False ONLY for direct job requisition endpoints with specific job IDs.
    """
    if url.startswith("mailto:"):
        return False

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    query = parsed.query.lower()
    parts = [p for p in path.split("/") if p]

    # 1. Greenhouse
    if "greenhouse.io" in domain:
        if "gh_jid=" in query:
            return False
        if len(parts) >= 3 and parts[1] == "jobs":
            return False
        return True

    # 2. Ashby
    if "ashbyhq.com" in domain:
        if len(parts) >= 2:
            return False
        return True

    # 3. Lever
    if "lever.co" in domain:
        if len(parts) >= 2:
            return False
        return True

    # 4. Workday
    if "myworkdayjobs.com" in domain:
        if "/job/" in path:
            return False
        return True

    # 5. Workable
    if "workable.com" in domain:
        if "/j/" in path and len(parts) >= 3:
            return False
        return True

    # 6. Rippling
    if "rippling.com" in domain:
        if "/jobs/" in path and len(parts) >= 3:
            return False
        return True

    # 7. SmartRecruiters
    if "smartrecruiters.com" in domain:
        if len(parts) >= 2:
            return False
        return True

    # 8. Personio
    if "personio.de" in domain or "personio.com" in domain:
        if "/job/" in path and len(parts) >= 2:
            return False
        return True

    # 9. Generic career portals
    if domain in ["amazon.jobs", "careers.google.com", "jobs.apple.com", "careers.microsoft.com", "meta.com/careers"]:
        if not path or path in ["", "/", "/careers", "/jobs"]:
            return True

    if path in ["/careers", "/jobs", "/careers/all", "/jobs/all", "/careers/openings", "/jobs/openings"]:
        if "gh_jid=" not in query and "job_id=" not in query:
            return True

    if RE_CAREER_HOMEPAGE_PATHS.match(path):
        if "gh_jid=" not in query and "job_id=" not in query:
            return True

    return False

def verify_html_content(status_code: int, html_text: str, url: str) -> Tuple[bool, str]:
    """Validates the HTML response for live active requisition indicators."""
    if status_code != 200:
        return False, f"HTTP status {status_code} is not 200"

    if is_career_homepage(url):
        return False, "Target is a top-level career homepage, not a direct requisition"

    lower = html_text.lower()

    # Check for closed position banners
    for indicator in CLOSED_INDICATORS:
        if indicator in lower:
            return False, f"Requisition closed: '{indicator}' detected"

    # Patch 1: Trust known ATS direct URLs or JSON-LD JobPosting schema without requiring client-side form text
    parsed_domain = urlparse(url).netloc.lower()
    if any(ats in parsed_domain for ats in KNOWN_ATS_DOMAINS):
        return True, "Active ATS direct requisition verified"

    if '"@type": "jobposting"' in lower or '"@type":"jobposting"' in lower:
        return True, "Active Schema.org JobPosting verified"

    # Fallback to apply triggers
    has_apply_action = any(tag in lower for tag in APPLY_TRIGGERS)
    if not has_apply_action:
        return False, "No active application form or Apply button found"

    return True, "Active requisition verified"

async def verify_requisition_link(client: httpx.AsyncClient, url: str) -> Tuple[bool, str]:
    """Live asynchronous fetch gate enforcing RULE[user_global]."""
    if url.startswith("mailto:"):
        return True, "Valid direct founder email link"

    if is_career_homepage(url):
        return False, "URL rejected: Top-level career homepage"

    try:
        res = await client.get(url, follow_redirects=True, timeout=10.0)
        final_url = str(res.url)

        if is_career_homepage(final_url):
            return False, f"Redirected to career homepage: {final_url}"

        return verify_html_content(res.status_code, res.text, final_url)
    except httpx.RequestError as exc:
        return False, f"Network verification failure: {str(exc)}"
