import re
import httpx
from typing import List, Tuple, Dict, Any, Optional
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text
from ..analyzer.geo_filter import evaluate_geo_and_auth
from ..database import generate_job_id
from ..resolvers.workable import is_valid_workable_slug

NEWGRAD_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
SUMMER_2027_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"
SUMMER_2026_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"

RE_ATS_ASHBY = re.compile(r'(?:jobs|app)\.ashbyhq\.com/([^/?#]+)', re.I)
RE_ATS_GREENHOUSE = re.compile(r'(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([^/?#]+)', re.I)
RE_ATS_LEVER = re.compile(r'jobs\.lever\.co/([^/?#]+)', re.I)
RE_ATS_WORKDAY = re.compile(r'([a-zA-Z0-9_\-\.]+)\.myworkdayjobs\.com', re.I)
RE_ATS_WORKABLE = re.compile(r'apply\.workable\.com/([^/?#]+)', re.I)
RE_ATS_RIPPLING = re.compile(r'ats\.rippling\.com/(?:api/v2/board/)?([^/?#]+)', re.I)
RE_ATS_SMARTRECRUITERS = re.compile(r'jobs\.smartrecruiters\.com/([^/?#]+)', re.I)
RE_ATS_PERSONIO = re.compile(r'([a-zA-Z0-9_\-\.]+)\.jobs\.personio\.(?:de|com)', re.I)
RE_ATS_RECRUITEE = re.compile(r'([a-zA-Z0-9_\-\.]+)\.recruitee\.com', re.I)

def parse_simplify_item(item: Dict[str, Any]) -> Tuple[Optional[JobRequisition], Optional[Dict[str, str]]]:
    """
    Parses a single Simplify listing item.
    Returns: (JobRequisition or None, company_dict or None)
    """
    if not item.get("active", False):
        return None, None

    title = item.get("title", "")
    company_name = item.get("company_name", "")
    url = item.get("url", "")
    locations = item.get("locations", [])
    loc_str = " / ".join(locations) if isinstance(locations, list) else str(locations or "Remote")

    if not url or not company_name or not title:
        return None, None

    # Detect ATS slug
    ats_type = "Direct ATS"
    slug = ""
    new_company = None

    if m := RE_ATS_ASHBY.search(url):
        ats_type = "Ashby"
        slug = m.group(1).lower()
    elif m := RE_ATS_GREENHOUSE.search(url):
        ats_type = "Greenhouse"
        slug = m.group(1).lower()
    elif m := RE_ATS_LEVER.search(url):
        ats_type = "Lever"
        slug = m.group(1).lower()
    elif m := RE_ATS_WORKDAY.search(url):
        ats_type = "Workday"
        slug = m.group(1).lower()
    elif m := RE_ATS_WORKABLE.search(url):
        candidate_slug = m.group(1).lower()
        if is_valid_workable_slug(candidate_slug):
            ats_type = "Workable"
            slug = candidate_slug
    elif m := RE_ATS_RIPPLING.search(url):
        ats_type = "Rippling"
        slug = m.group(1).lower()
    elif m := RE_ATS_SMARTRECRUITERS.search(url):
        ats_type = "SmartRecruiters"
        slug = m.group(1).lower()
    elif m := RE_ATS_PERSONIO.search(url):
        ats_type = "Personio"
        slug = m.group(1).lower()
    elif m := RE_ATS_RECRUITEE.search(url):
        ats_type = "Recruitee"
        slug = m.group(1).lower()

    if slug and slug not in ["jobs", "embed", "job_board", "j", "api"]:
        new_company = {
            "name": company_name,
            "slug": slug,
            "ats": ats_type.lower(),
            "is_top_tier": False,
            "domain": f"{company_name} Engineering",
            "discovered_from": "simplify_feed"
        }

    is_intern = bool(re.search(r'\b(intern|internship|co-op|trainee)\b', title, re.I))

    # Evaluate geo & auth before discovering company slug
    is_geo_valid, _, _, _ = evaluate_geo_and_auth(loc_str, is_internship=is_intern)
    if not is_geo_valid:
        new_company = None

    job_id = generate_job_id(company_name, title, url)
    posted_date = str(item.get("date_posted") or item.get("date_updated") or "")

    terms = item.get("terms", [])
    terms_str = ", ".join(terms) if isinstance(terms, list) else str(terms or "")
    sponsorship = item.get("sponsorship", "")
    extra_parts = []
    if terms_str:
        extra_parts.append(f"Terms: {terms_str}")
    if sponsorship:
        extra_parts.append(f"Sponsorship: {sponsorship}")
    extra_text = f" ({'; '.join(extra_parts)})" if extra_parts else ""

    job = JobRequisition(
        id=job_id,
        company=company_name,
        title=title,
        location=loc_str,
        apply_url=url,
        description_text=f"{company_name} {title} - {loc_str}{extra_text}",
        is_internship=is_intern,
        ats=ats_type,
        posted_date=posted_date
    )
    return job, new_company

async def fetch_simplify_jobs(client: httpx.AsyncClient) -> Tuple[List[JobRequisition], List[Dict[str, str]]]:
    """Fetches active software listings from Simplify open repos."""
    all_jobs = []
    new_companies = []
    seen_urls = set()

    for feed_url in [SUMMER_2027_URL, SUMMER_2026_URL, NEWGRAD_URL]:
        try:
            res = await client.get(feed_url, timeout=15.0)
            if res.status_code != 200:
                continue
            data = res.json()
            if not isinstance(data, list):
                continue

            for item in data:
                job, new_comp = parse_simplify_item(item)
                if job and job.apply_url not in seen_urls:
                    seen_urls.add(job.apply_url)
                    all_jobs.append(job)
                if new_comp:
                    new_companies.append(new_comp)
        except Exception:
            continue

    # Deduplicate discovered companies by (slug, ats)
    unique_companies = []
    seen_slug_ats = set()
    for comp in new_companies:
        key = (comp.get("slug", "").lower(), comp.get("ats", "").lower())
        if key not in seen_slug_ats:
            seen_slug_ats.add(key)
            unique_companies.append(comp)

    return all_jobs, unique_companies

fetch_simplify_feed = fetch_simplify_jobs

