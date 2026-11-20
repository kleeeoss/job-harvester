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
    "role is no longer open"
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

def is_career_homepage(url: str) -> bool:
    """
    Enforces RULE[user_global]:
    Detects top-level career homepages (e.g. company.com/careers, amazon.jobs).
    Returns False for direct job requisition endpoints.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()

    # Known direct ATS domains with job path segments
    if any(ats in domain for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com"]):
        # Direct ATS paths have job identifiers: /company/jobs/123 or /company/uuid
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            return False

    # Top-level career portals
    if domain in ["amazon.jobs", "careers.google.com", "jobs.apple.com", "careers.microsoft.com"]:
        if not path or path == "/":
            return True

    # Generic /careers or /jobs path without specific job ID
    if path in ["/careers", "/jobs", "/careers/all", "/jobs/all", "/careers/openings"]:
        return True

    if RE_CAREER_HOMEPAGE_PATHS.match(path):
        return True

    return False

def verify_html_content(status_code: int, html_text: str, url: str) -> Tuple[bool, str]:
    """
    Validates the HTML response for live active requisition indicators.
    """
    if status_code != 200:
        return False, f"HTTP status {status_code} is not 200"

    if is_career_homepage(url):
        return False, "Target is a top-level career homepage, not a direct requisition"

    lower = html_text.lower()

    # Check for closed position banners
    for indicator in CLOSED_INDICATORS:
        if indicator in lower:
            return False, f"Requisition closed: '{indicator}' detected"

    # Check for active application trigger or form
    has_apply_action = any(tag in lower for tag in APPLY_TRIGGERS)
    if not has_apply_action:
        return False, "No active application form or Apply button found"

    return True, "Active requisition verified"

async def verify_requisition_link(client: httpx.AsyncClient, url: str) -> Tuple[bool, str]:
    """
    Live asynchronous fetch gate enforcing RULE[user_global]:
    1. HTTP Status 200
    2. Not redirected to generic career page
    3. Active Apply button / form present
    4. Not marked as filled
    """
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
