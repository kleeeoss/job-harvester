import re
import httpx
from typing import List, Dict, Any
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

def parse_workday_payload(company_slug: str, data: Dict[str, Any]) -> List[JobRequisition]:
    """
    Parses Workday job posting payloads.
    Enforces RULE[user_global]: Must verify postingAvailable is True.
    If postingAvailable is False, the job is closed and must be excluded.
    """
    jobs = []
    if not isinstance(data, dict):
        return []

    posting_info = data.get("jobPostingInfo")
    if not posting_info or not isinstance(posting_info, dict):
        return []

    if not posting_info.get("postingAvailable", False):
        return []

    title = posting_info.get("title", "")
    location = posting_info.get("location", "")
    apply_url = posting_info.get("externalUrl", "")
    description_raw = posting_info.get("jobDescription", "")
    description_text = clean_text(description_raw)

    is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))

    jobs.append(JobRequisition(
        id=str(posting_info.get("jobReqId", "workday_req")),
        company=company_slug,
        title=title,
        location=location,
        apply_url=apply_url,
        description_text=description_text,
        is_internship=is_internship,
        ats="Workday"
    ))
    return jobs

async def fetch_workday_jobs(client: httpx.AsyncClient, company: Dict[str, Any]) -> List[JobRequisition]:
    """
    Fetches job listings from Workday Candidate Experience Services (CXS) API.
    For each job, verifies jobPostingInfo.postingAvailable is True.
    """
    slug = company.get("slug", "")
    api_url = company.get("api_url")
    if not api_url:
        return []

    try:
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
        res = await client.post(api_url, json=payload, timeout=10.0)
        if res.status_code != 200:
            return []

        data = res.json()
        job_postings = data.get("jobPostings", [])
        jobs = []

        base_detail_url = api_url.rstrip("/")
        if base_detail_url.endswith("/jobs"):
            base_detail_url = base_detail_url[:-5]

        for item in job_postings:
            ext_path = item.get("externalPath", "")
            if not ext_path:
                continue

            detail_endpoint = f"{base_detail_url}{ext_path}"
            detail_res = await client.get(detail_endpoint, timeout=8.0)
            if detail_res.status_code == 200:
                parsed = parse_workday_payload(slug, detail_res.json())
                jobs.extend(parsed)

        return jobs
    except Exception:
        return []
