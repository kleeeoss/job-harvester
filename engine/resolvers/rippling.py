import asyncio
import re
import httpx
from typing import List, Dict, Any, Set
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

async def fetch_rippling_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """
    Rippling 2-Pass Resolver with multi-location ID deduplication.
    Pass 1: Paginate job listings (page=0, pageSize=100).
    Pass 2: Fetch detailed description only for engineering roles.
    """
    base_url = f"https://ats.rippling.com/api/v2/board/{company_slug}/jobs"
    page = 0
    all_raw_jobs = []
    seen_ids: Set[str] = set()

    try:
        while True:
            url = f"{base_url}?page={page}&pageSize=100"
            res = await client.get(url, timeout=10.0)
            if res.status_code != 200:
                break
            data = res.json()
            items = data if isinstance(data, list) else data.get("jobs", [])
            if not items:
                break

            for item in items:
                job_id = str(item.get("id", ""))
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                all_raw_jobs.append(item)

            if len(items) < 100 or page >= 3:
                break
            page += 1
    except Exception:
        pass

    if not all_raw_jobs:
        return []

    # Filter to candidate roles before Pass 2
    from ..analyzer.eligibility import is_engineering_role
    candidate_items = [
        item for item in all_raw_jobs
        if is_engineering_role(item.get("name", item.get("title", "")))
    ]

    if not candidate_items:
        return []

    detail_sem = asyncio.Semaphore(10)

    async def fetch_rippling_detail(item: Dict[str, Any]) -> JobRequisition:
        job_id = str(item.get("id", ""))
        title = item.get("name") or item.get("title") or ""
        workplace_type = item.get("workplaceType", "")
        locations_list = [loc.get("name", "") for loc in item.get("locations", []) if isinstance(loc, dict)]
        location_base = " / ".join(locations_list) if locations_list else "Remote"

        is_remote = "remote" in workplace_type.lower() or "remote" in location_base.lower()
        if is_remote and "remote" not in location_base.lower():
            location = f"{location_base} (Remote)"
        else:
            location = location_base

        apply_url = f"https://ats.rippling.com/{company_slug}/jobs/{job_id}"
        description_text = f"Position at {company_slug}: {title}"
        posted_date = str(item.get("createdAt") or "")

        # Pass 2: Concurrently fetch detail for description
        detail_url = f"{base_url}/{job_id}"
        try:
            async with detail_sem:
                d_res = await client.get(detail_url, timeout=8.0)
                if d_res.status_code == 200:
                    d_data = d_res.json()
                    raw_html = d_data.get("descriptionHtml") or d_data.get("description") or ""
                    if raw_html:
                        description_text = clean_text(raw_html)
        except Exception:
            pass

        is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))

        return JobRequisition(
            id=job_id,
            company=company_slug,
            title=title,
            location=location,
            apply_url=apply_url,
            description_text=description_text,
            is_internship=is_internship,
            ats="Rippling",
            posted_date=posted_date
        )

    jobs = await asyncio.gather(*[fetch_rippling_detail(item) for item in candidate_items], return_exceptions=True)
    return [j for j in jobs if isinstance(j, JobRequisition)]
