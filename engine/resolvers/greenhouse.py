import re
import httpx
from typing import List, Dict, Any
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

def parse_greenhouse_payload(company_slug: str, data: Dict[str, Any]) -> List[JobRequisition]:
    jobs = []
    job_list = data.get("jobs", []) if isinstance(data, dict) else []
    for item in job_list:
        job_id = str(item.get("id", ""))
        title = item.get("title", "")
        loc_obj = item.get("location")
        location = loc_obj.get("name", "") if isinstance(loc_obj, dict) else str(loc_obj or "")

        apply_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{company_slug}/jobs/{job_id}"
        description_raw = item.get("content", "")
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
            ats="Greenhouse"
        ))
    return jobs

async def fetch_greenhouse_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code == 200:
            return parse_greenhouse_payload(company_slug, res.json())
        return []
    except Exception:
        return []
