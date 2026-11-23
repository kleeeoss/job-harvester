import asyncio
import re
import httpx
from typing import List, Dict, Any, Set, Optional
from ..models import JobRequisition, PayTier
from ..analyzer.text_extractor import clean_text

RESERVED_WORKABLE_SLUGS: Set[str] = {
    "j", "api", "view", "embed", "widget", "accounts", "jobs", "careers", "search"
}

_WORKABLE_SEMAPHORES: Dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}

def get_workable_semaphore() -> asyncio.Semaphore:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.Semaphore(2)
    if loop not in _WORKABLE_SEMAPHORES:
        _WORKABLE_SEMAPHORES[loop] = asyncio.Semaphore(2)
    return _WORKABLE_SEMAPHORES[loop]

def is_valid_workable_slug(slug: str) -> bool:
    """Verifies that an auto-discovered slug is not a reserved path."""
    if not slug:
        return False
    s = slug.lower().strip()
    return s not in RESERVED_WORKABLE_SLUGS and len(s) >= 3

def parse_workable_payload(company_slug: str, data: Dict[str, Any]) -> List[JobRequisition]:
    jobs = []
    job_list = data.get("jobs", []) if isinstance(data, dict) else []
    seen_shortcodes = set()

    for item in job_list:
        shortcode = item.get("shortcode") or item.get("id") or ""
        if not shortcode or shortcode in seen_shortcodes:
            continue
        seen_shortcodes.add(shortcode)

        title = item.get("title", "")
        city = item.get("city", "")
        country = item.get("country", "")
        is_telecommuting = bool(item.get("telecommuting", False))

        loc_parts = [p for p in [city, country] if p]
        location_base = ", ".join(loc_parts) if loc_parts else "Remote"
        if is_telecommuting:
            location = f"{location_base} (Remote)" if "remote" not in location_base.lower() else location_base
        else:
            location = location_base

        shortlink = item.get("shortlink") or f"https://apply.workable.com/{company_slug}/j/{shortcode}/"
        description_raw = item.get("description", "")
        description_text = clean_text(description_raw)

        is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))
        posted_date = item.get("published_on") or item.get("created_at") or ""

        jobs.append(JobRequisition(
            id=str(shortcode),
            company=company_slug,
            title=title,
            location=location,
            apply_url=shortlink,
            description_text=description_text,
            is_internship=is_internship,
            ats="Workable",
            posted_date=str(posted_date)
        ))
    return jobs

async def fetch_workable_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """Fetches Workable public widget jobs capped to 1-2 concurrent calls to avoid WAF blocks."""
    if not is_valid_workable_slug(company_slug):
        return []

    url = f"https://apply.workable.com/api/v1/widget/accounts/{company_slug}?details=true"
    async with get_workable_semaphore():
        try:
            await asyncio.sleep(0.3)  # Polite delay
            res = await client.get(url, timeout=12.0)
            if res.status_code == 200:
                return parse_workable_payload(company_slug, res.json())
            return []
        except Exception:
            return []
