import re
import httpx
from typing import List, Any
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

def parse_lever_payload(company_slug: str, data: Any) -> List[JobRequisition]:
    jobs = []
    if not isinstance(data, list):
        return []
    for item in data:
        job_id = str(item.get("id", ""))
        title = item.get("text", "")
        cats = item.get("categories", {})
        location = cats.get("location", "") if isinstance(cats, dict) else ""
        apply_url = item.get("applyUrl") or item.get("hostedUrl") or f"https://jobs.lever.co/{company_slug}/{job_id}"

        description_raw = item.get("description", "")
        description_text = clean_text(description_raw)

        is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))
        posted_date = str(item.get("createdAt") or "")

        jobs.append(JobRequisition(
            id=job_id,
            company=company_slug,
            title=title,
            location=location,
            apply_url=apply_url,
            description_text=description_text,
            is_internship=is_internship,
            ats="Lever",
            posted_date=posted_date
        ))
    return jobs

async def fetch_lever_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code == 200:
            return parse_lever_payload(company_slug, res.json())
        return []
    except Exception:
        return []
