import re
import httpx
from typing import List
from ..models import JobRequisition
from .lever import parse_lever_payload

async def fetch_eu_lever_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """Fetches jobs from EU Lever endpoint (api.eu.lever.co)."""
    url = f"https://api.eu.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code == 200:
            jobs = parse_lever_payload(company_slug, res.json())
            for j in jobs:
                j.ats = "EU Lever"
            return jobs
        return []
    except Exception:
        return []
