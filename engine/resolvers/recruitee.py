import re
import httpx
from typing import List
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

async def fetch_recruitee_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """Fetches jobs from Recruitee public API: {slug}.recruitee.com/api/offers/"""
    url = f"https://{company_slug}.recruitee.com/api/offers/"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code != 200:
            return []
        data = res.json()
        offers = data.get("offers", []) if isinstance(data, dict) else []

        jobs = []
        for offer in offers:
            offer_id = str(offer.get("id", ""))
            title = offer.get("title", "")
            city = offer.get("city", "")
            country = offer.get("country", "")
            is_remote = offer.get("remote", False)

            loc_parts = [p for p in [city, country] if p]
            loc_base = ", ".join(loc_parts) if loc_parts else "Remote"
            location = f"{loc_base} (Remote)" if is_remote and "remote" not in loc_base.lower() else loc_base

            careers_url = offer.get("careers_url") or f"https://{company_slug}.recruitee.com/o/{offer.get('slug', offer_id)}"
            desc = clean_text(offer.get("description", ""))
            is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))
            posted_date = offer.get("published_at", "")

            jobs.append(JobRequisition(
                id=offer_id,
                company=company_slug,
                title=title,
                location=location,
                apply_url=careers_url,
                description_text=desc,
                is_internship=is_internship,
                ats="Recruitee",
                posted_date=posted_date
            ))
        return jobs
    except Exception:
        return []
