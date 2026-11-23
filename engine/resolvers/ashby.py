import re
import httpx
from typing import List, Dict, Any
from ..models import JobRequisition, PayTier
from ..analyzer.text_extractor import clean_text

def parse_ashby_payload(company_slug: str, data: Dict[str, Any]) -> List[JobRequisition]:
    jobs = []
    job_list = data.get("jobs", []) if isinstance(data, dict) else []
    for item in job_list:
        # Respect isListed gate: Drop unlisted / internal-only roles
        if item.get("isListed") is False:
            continue

        job_id = str(item.get("id", ""))
        title = item.get("title", "")
        primary_loc = item.get("location", "")
        secondary_locs = [
            loc.get("location", "") for loc in item.get("secondaryLocations", [])
            if isinstance(loc, dict) and loc.get("location")
        ]
        all_locs = [primary_loc] + [l for l in secondary_locs if l != primary_loc] if primary_loc else secondary_locs
        location_base = " / ".join(all_locs) if all_locs else "Remote"

        if item.get("isRemote"):
            if location_base:
                location = location_base if "remote" in location_base.lower() else f"{location_base} (Remote)"
            else:
                location = "Remote"
        else:
            location = location_base

        # Direct requisition URL
        apply_url = item.get("applyUrl") or item.get("jobUrl") or f"https://jobs.ashbyhq.com/{company_slug}/{job_id}/application"
        description_raw = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
        description_text = clean_text(description_raw)

        is_internship = bool(re.search(r'\b(interns?|internships?|co-op|trainee)\b', title, re.I))

        # Check structured compensation from Ashby API
        compensation_str = "[Unlisted Salary: Venture-Backed Competitive]"
        pay_tier = PayTier.INTERN_UNLISTED if is_internship else PayTier.JOB_UNLISTED

        comp_data = item.get("compensation")
        if isinstance(comp_data, dict):
            summary = comp_data.get("scrapeableCompensationSalarySummary") or comp_data.get("compensationTierSummary")
            if summary:
                compensation_str = summary
                # Check for USD / annual
                m_usd = re.search(r'\$([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})[kK]?\s*[-–—]\s*\$([0-9]{1,3}(?:,[0-9]{3})*|[0-9]{2,6})[kK]?', summary)
                if m_usd:
                    min_str = m_usd.group(1).replace(",", "")
                    min_val = int(min_str) * 1000 if int(min_str) < 1000 else int(min_str)
                    approx_lpa = int((min_val * 83) / 100000)
                    if approx_lpa >= 45:
                        pay_tier = PayTier.JOB_45_60_LPA
                    elif approx_lpa >= 30:
                        pay_tier = PayTier.JOB_30_45_LPA
                    elif approx_lpa >= 15:
                        pay_tier = PayTier.JOB_15_30_LPA
                    else:
                        pay_tier = PayTier.JOB_10_15_LPA

        posted_date = item.get("publishedAt") or item.get("createdAt")

        jobs.append(JobRequisition(
            id=job_id,
            company=company_slug,
            title=title,
            location=location,
            apply_url=apply_url,
            description_text=description_text,
            is_internship=is_internship,
            pay_tier=pay_tier,
            compensation_str=compensation_str,
            ats="Ashby",
            posted_date=str(posted_date) if posted_date else ""
        ))
    return jobs

async def fetch_ashby_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}?includeCompensation=true"
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code == 200:
            return parse_ashby_payload(company_slug, res.json())
        return []
    except Exception:
        return []
