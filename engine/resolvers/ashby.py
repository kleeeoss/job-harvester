import re
import httpx
from typing import List, Dict, Any
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

def parse_ashby_payload(company_slug: str, data: Dict[str, Any]) -> List[JobRequisition]:
    jobs = []
    job_list = data.get("jobs", []) if isinstance(data, dict) else []
    for item in job_list:
        job_id = str(item.get("id", ""))
        title = item.get("title", "")
        location = item.get("location", "")
        if item.get("isRemote"):
            location = f"{location} (Remote)".strip() if location else "Remote"

        # Direct requisition URL
        apply_url = item.get("applyUrl") or item.get("jobUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{job_id}"
        description_raw = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
        description_text = clean_text(description_raw)

        is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))

        jobs.append(JobRequisition(
            id=job_id,
            company=company_slug,
            title=title,
            location=location,
            apply_url=apply_url,
            description_text=description_text,
            is_internship=is_internship,
            ats="Ashby"
        ))
    return jobs

async def fetch_ashby_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code == 200:
            return parse_ashby_payload(company_slug, res.json())
        return []
    except Exception:
        return []
