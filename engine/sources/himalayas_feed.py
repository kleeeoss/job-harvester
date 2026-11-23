import re
import httpx
from typing import List, Tuple, Dict, Any, Optional
from ..models import JobRequisition, PayTier
from ..analyzer.text_extractor import clean_text
from ..database import generate_job_id

HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"

HIMALAYAS_SEARCH_QUERIES = [
    # 1. India Internships (Pages 1..3)
    [f"employment_type=Intern&country=IN&sort=recent&page={p}" for p in range(1, 4)],
    # 2. Worldwide Remote Internships (Pages 1..2)
    [f"employment_type=Intern&worldwide=true&sort=recent&page={p}" for p in range(1, 3)],
    # 3. India Entry-Level Roles (Pages 1..2)
    [f"seniority=Entry-level&country=IN&sort=recent&page={p}" for p in range(1, 3)],
]

RE_ATS_DOMAINS = re.compile(
    r'(?:jobs\.ashbyhq\.com|boards\.greenhouse\.io|jobs\.lever\.co|apply\.workable\.com|ats\.rippling\.com)/([^/?#]+)',
    re.I
)

def parse_himalayas_item(item: Dict[str, Any]) -> Optional[JobRequisition]:
    """Parses a single job item from Himalayas API with location and salary mapping."""
    if not isinstance(item, dict):
        return None

    title = item.get("title", "")
    company_name = item.get("companyName", "")
    apply_url = item.get("applicationLink") or item.get("url") or item.get("guid") or ""
    if not title or not company_name or not apply_url:
        return None

    loc_restrictions = item.get("locationRestrictions", [])
    if isinstance(loc_restrictions, list) and loc_restrictions:
        mapped_locs = []
        for l in loc_restrictions:
            s = str(l).strip()
            if s.upper() == "IN":
                mapped_locs.append("India")
            else:
                mapped_locs.append(s)
        location_raw = " / ".join(mapped_locs)
    elif isinstance(loc_restrictions, str) and loc_restrictions.strip():
        s = loc_restrictions.strip()
        location_raw = "India" if s.upper() == "IN" else s
    else:
        location_raw = "Worldwide Remote"

    # Himalayas is 100% remote: ensure "(Remote)" is appended if not already remote/worldwide/anywhere
    loc_lower = location_raw.lower()
    if not any(w in loc_lower for w in ["remote", "worldwide", "anywhere"]):
        location = f"{location_raw} (Remote)"
    else:
        location = location_raw

    raw_desc = item.get("description", "")
    desc_clean = clean_text(raw_desc)

    emp_type = item.get("employmentType", "")
    is_intern = bool(re.search(r'\b(intern|internship|co-op|trainee)\b', f"{title} {emp_type}", re.I))

    # Detect ATS
    ats = "Himalayas"
    m_ats = RE_ATS_DOMAINS.search(apply_url) or RE_ATS_DOMAINS.search(raw_desc)
    if m_ats:
        matched_str = m_ats.group(0).lower()
        if "ashby" in matched_str:
            ats = "Ashby"
        elif "greenhouse" in matched_str:
            ats = "Greenhouse"
        elif "lever" in matched_str:
            ats = "Lever"
        elif "workable" in matched_str:
            ats = "Workable"
        elif "rippling" in matched_str:
            ats = "Rippling"

    sal_min = item.get("minSalary") if item.get("minSalary") is not None else item.get("salaryMin")
    sal_max = item.get("maxSalary") if item.get("maxSalary") is not None else item.get("salaryMax")
    period = (item.get("salaryPeriod") or "annual").lower()
    currency = item.get("currency") or "USD"

    compensation_str = "[Unlisted Stipend]" if is_intern else "[Unlisted Salary]"
    pay_tier = PayTier.INTERN_UNLISTED if is_intern else PayTier.JOB_UNLISTED

    if sal_min is not None:
        try:
            val_min = int(sal_min)
            val_max = int(sal_max) if sal_max is not None else val_min

            if is_intern:
                # Calculate monthly value in INR
                if currency.upper() == "INR":
                    monthly_val = val_min if period == "monthly" else val_min // 12
                    compensation_str = f"₹{val_min:,} - ₹{val_max:,} / month" if sal_max else f"₹{val_min:,} / month"
                else:  # USD or foreign
                    monthly_usd = val_min if period == "monthly" else val_min // 12
                    monthly_val = int(monthly_usd * 83)
                    compensation_str = f"${val_min:,} - ${val_max:,}/mo" if sal_max else f"${val_min:,}/mo"

                if monthly_val >= 40000:
                    pay_tier = PayTier.INTERN_40K_50K
                elif monthly_val >= 30000:
                    pay_tier = PayTier.INTERN_30K_40K
                elif monthly_val >= 20000:
                    pay_tier = PayTier.INTERN_20K_30K
                elif monthly_val >= 10000:
                    pay_tier = PayTier.INTERN_10K_20K
            else:
                # Full-time annual LPA
                if currency.upper() == "USD":
                    annual_usd = val_min * 12 if period == "monthly" else val_min
                    approx_lpa = int((annual_usd * 83) / 100000)
                    compensation_str = f"${val_min:,} - ${val_max:,}" if sal_max else f"${val_min:,}"
                else:  # INR
                    annual_inr = val_min * 12 if period == "monthly" else val_min
                    approx_lpa = int(annual_inr / 100000)
                    compensation_str = f"₹{val_min:,} - ₹{val_max:,}" if sal_max else f"₹{val_min:,}"

                if approx_lpa >= 45:
                    pay_tier = PayTier.JOB_45_60_LPA
                elif approx_lpa >= 30:
                    pay_tier = PayTier.JOB_30_45_LPA
                elif approx_lpa >= 15:
                    pay_tier = PayTier.JOB_15_30_LPA
                elif approx_lpa >= 10:
                    pay_tier = PayTier.JOB_10_15_LPA
        except (ValueError, TypeError):
            pass

    job_id = generate_job_id(company_name, title, apply_url)
    pub_date = item.get("pubDate")
    posted_date = str(pub_date) if pub_date else ""

    return JobRequisition(
        id=job_id,
        company=company_name,
        title=title,
        location=location,
        apply_url=apply_url,
        description_text=desc_clean,
        is_internship=is_intern,
        pay_tier=pay_tier,
        compensation_str=compensation_str,
        ats=ats,
        posted_date=posted_date,
        is_verified=True
    )

async def fetch_himalayas_jobs(client: httpx.AsyncClient) -> Tuple[List[JobRequisition], List[Dict[str, str]]]:
    """Fetches targeted internships and entry-level jobs from Himalayas Search API."""
    all_jobs = []
    new_companies = []
    seen_urls = set()

    query_params = []
    for q_list in HIMALAYAS_SEARCH_QUERIES:
        query_params.extend(q_list)

    for q in query_params:
        url = f"{HIMALAYAS_SEARCH_URL}?{q}"
        try:
            res = await client.get(url, timeout=12.0)
            if res.status_code != 200:
                continue
            data = res.json()
            raw_jobs = data.get("jobs", []) if isinstance(data, dict) else []
            for item in raw_jobs:
                job = parse_himalayas_item(item)
                if job and job.apply_url not in seen_urls:
                    seen_urls.add(job.apply_url)
                    all_jobs.append(job)

                    # Check if ATS domain discovered
                    raw_desc = item.get("description", "")
                    m_slug = RE_ATS_DOMAINS.search(job.apply_url) or RE_ATS_DOMAINS.search(raw_desc)
                    if m_slug:
                        slug = m_slug.group(1).lower()
                        matched_str = m_slug.group(0).lower()
                        ats_name = "greenhouse"
                        if "ashby" in matched_str:
                            ats_name = "ashby"
                        elif "lever" in matched_str:
                            ats_name = "lever"
                        elif "workable" in matched_str:
                            ats_name = "workable"
                        elif "rippling" in matched_str:
                            ats_name = "rippling"

                        if slug not in ["jobs", "embed", "job_board", "j", "api"]:
                            new_companies.append({
                                "name": job.company,
                                "slug": slug,
                                "ats": ats_name,
                                "is_top_tier": False,
                                "domain": f"{job.company} Engineering",
                                "discovered_from": "himalayas_feed"
                            })
        except Exception:
            continue

    return all_jobs, new_companies
