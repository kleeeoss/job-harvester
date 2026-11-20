import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Optional
import httpx

from config.settings import (
    PROFILE,
    TOP_TIER_COMPANIES,
    TOP_TIER_MIN_LPA,
    TOP_TIER_MIN_STIPEND_INR
)
from .models import JobRequisition, HarvestResult, PayTier
from .analyzer.eligibility import check_eligibility
from .analyzer.location import check_location
from .analyzer.compensation import parse_compensation
from .analyzer.tech_scorer import score_tech_stack
from .verifier.link_verifier import verify_requisition_link, is_career_homepage
from .resolvers.ashby import fetch_ashby_jobs
from .resolvers.greenhouse import fetch_greenhouse_jobs
from .resolvers.lever import fetch_lever_jobs
from .output.markdown_gen import generate_harvest_report

RE_NON_TECH = re.compile(
    r'\b(marketing|product\s*manager|user\s*research|brand|communication|'
    r'sales|recruiter|talent|account\s*executive|legal|finance|operations|'
    r'business\s*development|human\s*resources|hr|design(?:er|s|ing)?|product\s*designer|graphic|support|'
    r'customer\s*success|customer\s*support|accountant)\b',
    re.IGNORECASE
)

RE_ENGINEERING = re.compile(
    r'\b(software|backend|systems?|infrastructure|devops|cloud|platform|sre|'
    r'site\s*reliability|distributed|data\s*engineer|data\s*scientist|'
    r'machine\s*learning|ml|ai|kernel|compiler|runtime|mts|'
    r'member\s*of\s*technical\s*staff|technical\s*staff|developer|architect|engineer)\b',
    re.IGNORECASE
)

def is_engineering_role(title: str) -> bool:
    title_clean = title.strip()
    if RE_NON_TECH.search(title_clean):
        if not re.search(r'\b(software\s*engineer|systems\s*engineer|backend\s*engineer)\b', title_clean, re.I):
            return False
    if re.search(r'\bintern\b', title_clean, re.I):
        return bool(RE_ENGINEERING.search(title_clean)) or bool(re.search(r'\b(tech|engineer|developer)\b', title_clean, re.I))
    return bool(RE_ENGINEERING.search(title_clean))

class JobHarvester:
    def __init__(self, companies_file: Optional[str] = None):
        if not companies_file:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            companies_file = os.path.join(base_dir, "config", "companies.json")
        self.companies_file = companies_file

    def load_companies(self, filter_company: Optional[str] = None) -> List[dict]:
        with open(self.companies_file, "r", encoding="utf-8") as f:
            companies = json.load(f)
        if filter_company:
            filter_lower = filter_company.lower()
            companies = [c for c in companies if filter_lower in c.get("name", "").lower() or filter_lower in c.get("slug", "").lower()]
        return companies

    async def fetch_company_jobs(self, client: httpx.AsyncClient, company: dict) -> List[JobRequisition]:
        ats = company.get("ats", "").lower()
        slug = company.get("slug", "")
        name = company.get("name", slug)

        jobs = []
        if ats == "ashby":
            raw_jobs = await fetch_ashby_jobs(client, slug)
        elif ats == "greenhouse":
            raw_jobs = await fetch_greenhouse_jobs(client, slug)
        elif ats == "lever":
            raw_jobs = await fetch_lever_jobs(client, slug)
        else:
            raw_jobs = []

        for j in raw_jobs:
            j.company = name
            jobs.append(j)
        return jobs

    async def run(
        self,
        filter_company: Optional[str] = None,
        max_companies: Optional[int] = None,
        verify_links: bool = True
    ) -> HarvestResult:
        companies = self.load_companies(filter_company)
        if max_companies:
            companies = companies[:max_companies]

        all_candidate_jobs: List[JobRequisition] = []
        closed_companies: List[str] = []
        total_scanned = 0

        async with httpx.AsyncClient(timeout=12.0) as client:
            for idx, company in enumerate(companies, 1):
                comp_name = company.get("name", "")
                ats = company.get("ats", "")
                print(f"[{idx}/{len(companies)}] Fetching {comp_name} ({ats.upper()})...", end="", flush=True)
                raw_jobs = await self.fetch_company_jobs(client, company)
                total_scanned += len(raw_jobs)
                print(f" Found {len(raw_jobs)} total listings.", flush=True)

                company_matches = []
                for job in raw_jobs:
                    # 1. Filter out non-technical roles
                    if not is_engineering_role(job.title):
                        continue

                    # 2. Check full text eligibility (citizenship, CGPA, graduation batch)
                    eligible, elig_reason = check_eligibility(job.description_text, job.is_internship)
                    if not eligible:
                        continue

                    # 3. Check location (India remote & on-site allowed; Foreign strictly 100% fully remote)
                    loc_valid, loc_type, loc_reason = check_location(job.location, job.description_text)
                    if not loc_valid:
                        continue
                    job.location_type = loc_type

                    # 4. Parse compensation & assign pay tier
                    comp_valid, pay_tier, comp_str, comp_reason = parse_compensation(job.description_text, job.is_internship)
                    if not comp_valid:
                        continue
                    job.pay_tier = pay_tier
                    job.compensation_str = comp_str

                    # 5. Score technical match
                    tech_score, keywords, rationale = score_tech_stack(job.title, job.description_text)
                    job.match_rationale = rationale

                    # 6. Check top-tier qualification
                    is_top_company = company.get("is_top_tier", False) or comp_name.lower() in TOP_TIER_COMPANIES
                    is_high_pay_job = (not job.is_internship) and (pay_tier in [PayTier.JOB_15_30_LPA, PayTier.JOB_30_60_LPA])
                    is_high_pay_intern = job.is_internship and (pay_tier == PayTier.INTERN_30K_50K)

                    if is_top_company or is_high_pay_job or is_high_pay_intern:
                        job.is_top_tier = True

                    # Ensure direct requisition link, not career homepage
                    if is_career_homepage(job.apply_url):
                        continue

                    company_matches.append(job)

                # 7. Live Link Verification Gate (RULE[user_global])
                verified_company_jobs = []
                if verify_links and company_matches:
                    sem = asyncio.Semaphore(8)
                    async def verify_one(job):
                        async with sem:
                            is_valid, reason = await verify_requisition_link(client, job.apply_url)
                            if is_valid:
                                job.is_verified = True
                                return job
                            return None

                    verify_results = await asyncio.gather(*(verify_one(j) for j in company_matches), return_exceptions=True)
                    verified_company_jobs = [r for r in verify_results if isinstance(r, JobRequisition)]
                elif not verify_links:
                    for job in company_matches:
                        job.is_verified = True
                        verified_company_jobs.append(job)

                if verified_company_jobs:
                    all_candidate_jobs.extend(verified_company_jobs)
                else:
                    # Negative Finding Integrity (RULE[user_global])
                    closed_companies.append(comp_name)

        today_str = datetime.now().strftime("%Y-%m-%d")
        return HarvestResult(
            date_str=today_str,
            active_jobs=all_candidate_jobs,
            closed_companies=closed_companies,
            total_scanned=total_scanned
        )
