import re
import httpx
from typing import List
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

async def fetch_gem_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """Fetches jobs from Gem public API: api.gem.com/job_board/v0/{slug}/job_posts/"""
    url = f"https://api.gem.com/job_board/v0/{company_slug}/job_posts/"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code != 200:
            return []
        data = res.json()
        items = data if isinstance(data, list) else data.get("job_posts", [])

        jobs = []
        for item in items:
            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            location = item.get("location", "Remote")
            apply_url = item.get("absolute_url") or f"https://jobs.gem.com/{company_slug}/{job_id}"
            desc = clean_text(item.get("content", ""))
            is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))

            jobs.append(JobRequisition(
                id=job_id,
                company=company_slug,
                title=title,
                location=location,
                apply_url=apply_url,
                description_text=desc,
                is_internship=is_internship,
                ats="Gem"
            ))
        return jobs
    except Exception:
        return []
