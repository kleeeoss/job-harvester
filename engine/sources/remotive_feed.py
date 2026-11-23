import asyncio
import re
import httpx
from typing import List, Tuple, Dict, Any, Optional
from ..models import JobRequisition, PayTier
from ..analyzer.text_extractor import clean_text
from ..database import generate_job_id

REMOTIVE_URLS = [
    "https://remotive.com/api/remote-jobs?category=software-dev",
    "https://remotive.com/api/remote-jobs?search=intern"
]

RE_ATS_DOMAINS = re.compile(
    r'(?:jobs\.ashbyhq\.com|boards\.greenhouse\.io|jobs\.lever\.co|apply\.workable\.com|ats\.rippling\.com)/([^/?#]+)',
    re.I
)

def parse_remotive_item(item: Dict[str, Any]) -> Optional[JobRequisition]:
    """Parses a single job item from Remotive API."""
    if not isinstance(item, dict):
        return None

    title = item.get("title", "")
    company_name = item.get("company_name", "")
    url = item.get("url", "")
    if not title or not company_name or not url:
        return None

    # Remotive is 100% remote: ensure "(Remote)" is appended if not already remote/worldwide/anywhere
    loc_raw = (item.get("candidate_required_location") or "Worldwide Remote").strip()
    loc_lower = loc_raw.lower()
    if not any(w in loc_lower for w in ["remote", "worldwide", "anywhere"]):
        location = f"{loc_raw} (Remote)"
    else:
        location = loc_raw

    raw_desc = item.get("description", "")
    desc_clean = clean_text(raw_desc)

    is_intern = bool(re.search(r'\b(intern|internship|co-op|trainee)\b', f"{title} {item.get('job_type', '')}", re.I))

    # Detect if direct ATS link is embedded in description or URL
    ats = "Remotive"
    m_ats = RE_ATS_DOMAINS.search(raw_desc) or RE_ATS_DOMAINS.search(url)
    if m_ats:
        matched_str = m_ats.group(0).lower()
        if "ashby" in matched_str:
            ats = "Ashby"
        elif "greenhouse" in matched_str:
            ats = "Greenhouse"
        elif "lever" in matched_str:
            ats = "Lever"
        elif "workable" in matched_str:
            ats = "Workable"
        elif "rippling" in matched_str:
            ats = "Rippling"

    salary = item.get("salary") or ""
    compensation_str = salary if salary else ("[Unlisted Stipend]" if is_intern else "[Unlisted Salary]")
    pay_tier = PayTier.INTERN_UNLISTED if is_intern else PayTier.JOB_UNLISTED

    if salary and not is_intern:
        m_usd = re.search(r'\$([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})[kK]?', salary)
        if m_usd:
            min_str = m_usd.group(1).replace(",", "")
            min_val = int(min_str) * 1000 if int(min_str) < 1000 else int(min_str)
            approx_lpa = int((min_val * 83) / 100000)
            if approx_lpa >= 45:
                pay_tier = PayTier.JOB_45_60_LPA
            elif approx_lpa >= 30:
                pay_tier = PayTier.JOB_30_45_LPA
            elif approx_lpa >= 15:
                pay_tier = PayTier.JOB_15_30_LPA
            else:
                pay_tier = PayTier.JOB_10_15_LPA

    job_id = generate_job_id(company_name, title, url)
    posted_date = str(item.get("publication_date") or "")

    return JobRequisition(
        id=job_id,
        company=company_name,
        title=title,
        location=location,
        apply_url=url,
        description_text=desc_clean,
        is_internship=is_intern,
        pay_tier=pay_tier,
        compensation_str=compensation_str,
        ats=ats,
        posted_date=posted_date,
        is_verified=True
    )

async def fetch_remotive_jobs(client: httpx.AsyncClient) -> Tuple[List[JobRequisition], List[Dict[str, str]]]:
    """Fetches software development and internship jobs from Remotive API."""
    all_jobs = []
    new_companies = []
    seen_urls = set()

    for idx, url in enumerate(REMOTIVE_URLS):
        if idx > 0:
            await asyncio.sleep(1.0)
        try:
            res = await client.get(url, timeout=15.0)
            if res.status_code != 200:
                continue
            data = res.json()
            raw_jobs = data.get("jobs", []) if isinstance(data, dict) else []
            for item in raw_jobs:
                job = parse_remotive_item(item)
                if job and job.apply_url not in seen_urls:
                    seen_urls.add(job.apply_url)
                    all_jobs.append(job)

                    # Check if ATS domain discovered
                    raw_desc = item.get("description", "")
                    m_slug = RE_ATS_DOMAINS.search(raw_desc) or RE_ATS_DOMAINS.search(job.apply_url)
                    if m_slug:
                        slug = m_slug.group(1).lower()
                        matched_str = m_slug.group(0).lower()
                        ats_name = "greenhouse"
                        if "ashby" in matched_str:
                            ats_name = "ashby"
                        elif "lever" in matched_str:
                            ats_name = "lever"
                        elif "workable" in matched_str:
                            ats_name = "workable"
                        elif "rippling" in matched_str:
                            ats_name = "rippling"

                        if slug not in ["jobs", "embed", "job_board", "j", "api"]:
                            new_companies.append({
                                "name": job.company,
                                "slug": slug,
                                "ats": ats_name,
                                "is_top_tier": False,
                                "domain": f"{job.company} Engineering",
                                "discovered_from": "remotive_feed"
                            })
        except Exception:
            continue

    return all_jobs, new_companies
