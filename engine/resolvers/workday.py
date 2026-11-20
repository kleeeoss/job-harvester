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
