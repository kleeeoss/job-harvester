import asyncio
import re
import httpx
from typing import List, Dict, Any
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text
from ..analyzer.eligibility import is_engineering_role

async def fetch_smartrecruiters_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """
    Fetches jobs from SmartRecruiters public API with 2-pass detail fetching:
    Pass 1: List postings from /v1/companies/{company_slug}/postings.
    Pass 2: Concurrently fetch full description text for engineering roles via /v1/companies/{company_slug}/postings/{id}.
    """
    url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code != 200:
            return []
        data = res.json()
        content = data.get("content", []) if isinstance(data, dict) else []

        # Filter candidate engineering roles for Pass 2
        candidate_items = [
            item for item in content
            if is_engineering_role(item.get("name", ""))
        ]

        detail_sem = asyncio.Semaphore(10)

        async def fetch_detail(item: Dict[str, Any]) -> JobRequisition:
            job_id = str(item.get("id", ""))
            title = item.get("name", "")
            loc = item.get("location", {})
            city = loc.get("city", "")
            country = loc.get("country", "")
            is_remote = loc.get("remote", False)

            loc_parts = [p for p in [city, country] if p]
            loc_base = ", ".join(loc_parts) if loc_parts else "Remote"
            location = f"{loc_base} (Remote)" if is_remote and "remote" not in loc_base.lower() else loc_base

            apply_url = f"https://jobs.smartrecruiters.com/{company_slug}/{job_id}"
            is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))
            posted_date = str(item.get("releasedDate") or "")

            description_text = f"Engineering position at {company_slug}: {title}"
            try:
                async with detail_sem:
                    d_url = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings/{job_id}"
                    d_res = await client.get(d_url, timeout=8.0)
                    if d_res.status_code == 200:
                        detail_data = d_res.json()
                        job_ad = detail_data.get("jobAd", {})
                        sections = job_ad.get("sections", {})
                        desc_parts = []
                        for sec_name in ["jobDescription", "qualifications", "additionalInformation"]:
                            sec_obj = sections.get(sec_name, {})
                            if isinstance(sec_obj, dict):
                                text_val = sec_obj.get("text", "")
                                if text_val:
                                    desc_parts.append(text_val)
                        if desc_parts:
                            description_text = clean_text("\n".join(desc_parts))
            except Exception:
                pass

            return JobRequisition(
                id=job_id,
                company=company_slug,
                title=title,
                location=location,
                apply_url=apply_url,
                description_text=description_text,
                is_internship=is_internship,
                ats="SmartRecruiters",
                posted_date=posted_date
            )

        if not candidate_items:
            return []

        jobs = await asyncio.gather(*[fetch_detail(item) for item in candidate_items], return_exceptions=True)
        return [j for j in jobs if isinstance(j, JobRequisition)]
    except Exception:
        return []
