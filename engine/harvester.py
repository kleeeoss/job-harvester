import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import httpx

from config.settings import (
    PROFILE,
    TOP_TIER_COMPANIES,
    DEFAULT_MAX_ROLES_PER_COMPANY,
    MAX_CONCURRENT_COMPANIES,
    DEFAULT_HARVEST_LIMIT,
    MIN_SCORE_THRESHOLD,
    MIN_INTERN_SCORE_THRESHOLD,
    TIER_1_SCORE_THRESHOLD
)
from .models import JobRequisition, HarvestResult, PayTier
from .analyzer.eligibility import check_eligibility, is_engineering_role
from .analyzer.geo_filter import evaluate_geo_and_auth
from .analyzer.compensation import parse_compensation
from .analyzer.tech_scorer import score_job_requisition
from .verifier.link_verifier import verify_requisition_link, is_career_homepage
from .database import (
    init_db,
    upsert_companies,
    upsert_jobs,
    get_net_new_jobs,
    mark_jobs_reported,
    generate_job_id,
    get_unreported_job_ids,
    get_discovered_companies
)

# Direct ATS Resolvers
from .resolvers.ashby import fetch_ashby_jobs
from .resolvers.greenhouse import fetch_greenhouse_jobs
from .resolvers.lever import fetch_lever_jobs
from .resolvers.eu_lever import fetch_eu_lever_jobs
from .resolvers.workday import fetch_workday_jobs
from .resolvers.workable import fetch_workable_jobs
from .resolvers.rippling import fetch_rippling_jobs
from .resolvers.personio import fetch_personio_jobs
from .resolvers.smartrecruiters import fetch_smartrecruiters_jobs
from .resolvers.gem import fetch_gem_jobs
from .resolvers.recruitee import fetch_recruitee_jobs

# Dynamic Feeds
from .sources.simplify_feed import fetch_simplify_jobs as fetch_simplify_feed
from .sources.hn_feed import fetch_hn_who_is_hiring_jobs as fetch_hn_feed
from .sources.remotive_feed import fetch_remotive_jobs
from .sources.himalayas_feed import fetch_himalayas_jobs
fetch_simplify_jobs = fetch_simplify_feed
fetch_hn_who_is_hiring_jobs = fetch_hn_feed



class JobHarvester:
    def __init__(self, companies_file: Optional[str] = None):
        if not companies_file:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            companies_file = os.path.join(base_dir, "config", "companies.json")
        self.companies_file = companies_file
        self.internship_funnel: Dict[str, int] = {
            "seen": 0,
            "dropped_onsite": 0,
            "dropped_us_only": 0,
            "dropped_stale": 0,
            "dropped_low_score": 0,
            "kept": 0
        }
        init_db()

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
        try:
            if ats == "ashby":
                raw_jobs = await fetch_ashby_jobs(client, slug)
            elif ats == "greenhouse":
                raw_jobs = await fetch_greenhouse_jobs(client, slug)
            elif ats == "lever":
                raw_jobs = await fetch_lever_jobs(client, slug)
            elif ats in ["eu_lever", "eu-lever"]:
                raw_jobs = await fetch_eu_lever_jobs(client, slug)
            elif ats == "workday":
                raw_jobs = await fetch_workday_jobs(client, company)
            elif ats == "workable":
                raw_jobs = await fetch_workable_jobs(client, slug)
            elif ats == "rippling":
                raw_jobs = await fetch_rippling_jobs(client, slug)
            elif ats == "personio":
                raw_jobs = await fetch_personio_jobs(client, slug)
            elif ats == "smartrecruiters":
                raw_jobs = await fetch_smartrecruiters_jobs(client, slug)
            elif ats == "gem":
                raw_jobs = await fetch_gem_jobs(client, slug)
            elif ats == "recruitee":
                raw_jobs = await fetch_recruitee_jobs(client, slug)
            else:
                raw_jobs = []

            for j in raw_jobs:
                j.company = name
                # Direct ATS API results are already active
                j.is_verified = True
                if not j.id or j.id == "":
                    j.id = generate_job_id(j.company, j.title, j.apply_url)
                jobs.append(j)
        except Exception:
            pass
        return jobs

    def filter_and_score_job(self, job: JobRequisition) -> Optional[JobRequisition]:
        """
        Executes candidate evaluation & scoring pipeline:
        1. Internship detection & funnel tracking
        2. Engineering role filter
        3. Hard seniority & freshness checks (90d intern, 30d full-time)
        4. Strict Geo & Work-Auth evaluation (with legal footer immunity)
        5. Compensation parsing & structured pay tier preservation
        6. 0–100 Weighted systems scoring & thresholding (35 intern, 55 full-time)
        """
        # Ensure is_internship is accurately set
        if not job.is_internship and re.search(r'\b(interns?|internships?|co-op|trainee)\b', job.title, re.I):
            job.is_internship = True

        # 1. Engineering title filter
        if not is_engineering_role(job.title):
            return None

        if job.is_internship:
            self.internship_funnel["seen"] += 1

        # 2. Hard seniority & freshness checks
        eligible, elig_reason = check_eligibility(
            job.description_text,
            is_internship=job.is_internship,
            role_title=job.title,
            posted_date=job.posted_date,
            is_direct_ats=job.is_verified
        )
        if not eligible:
            if job.is_internship:
                if "stale" in elig_reason.lower() or "age" in elig_reason.lower() or "day" in elig_reason.lower():
                    self.internship_funnel["dropped_stale"] += 1
                else:
                    self.internship_funnel["dropped_us_only"] += 1
            return None

        # 3. Geo & Work-Auth filter (with legal footer immunity)
        geo_valid, loc_type, geo_reason, geo_boost = evaluate_geo_and_auth(
            job.location,
            job.description_text,
            is_internship=job.is_internship
        )
        if not geo_valid:
            if job.is_internship:
                if (
                    "restricted" in loc_type.lower() or "restricted" in geo_reason.lower() or
                    "us" in loc_type.lower() or "foreign" in loc_type.lower() or
                    "jurisdiction" in geo_reason.lower() or "visa" in geo_reason.lower()
                ):
                    self.internship_funnel["dropped_us_only"] += 1
                else:
                    self.internship_funnel["dropped_onsite"] += 1
            return None
        job.location_type = loc_type

        # 4. Compensation parsing & assign pay tier (preserving structured pay tiers)
        comp_valid, parsed_pay_tier, comp_str, comp_reason = parse_compensation(job.description_text, job.is_internship)
        if not comp_valid:
            return None

        # Only overwrite pay_tier if current is unlisted or parsed is specific
        if job.pay_tier in (PayTier.JOB_UNLISTED, PayTier.INTERN_UNLISTED) or parsed_pay_tier not in (PayTier.JOB_UNLISTED, PayTier.INTERN_UNLISTED):
            job.pay_tier = parsed_pay_tier

        if not job.compensation_str or job.compensation_str.startswith("[Unlisted"):
            job.compensation_str = comp_str

        # 5. 0–100 Comprehensive Weighted Scoring
        score, is_tier_1, breakdown, rationale = score_job_requisition(
            title=job.title,
            job_text=job.description_text,
            company=job.company,
            location_type=job.location_type,
            is_internship=job.is_internship,
            pay_tier_val=job.pay_tier.value,
            geo_boost=geo_boost,
            contact_email=job.contact_email
        )
        job.score = score
        job.is_tier_1 = is_tier_1
        job.score_breakdown = breakdown
        job.match_rationale = rationale

        # Check score threshold (drop < 35 for intern, < 55 for full-time)
        score_threshold = MIN_INTERN_SCORE_THRESHOLD if job.is_internship else MIN_SCORE_THRESHOLD
        if job.score < score_threshold:
            if job.is_internship:
                self.internship_funnel["dropped_low_score"] += 1
            return None

        # Drop career homepages
        if is_career_homepage(job.apply_url):
            return None

        if job.is_internship:
            self.internship_funnel["kept"] += 1

        if not job.id:
            job.id = generate_job_id(job.company, job.title, job.apply_url, email=job.contact_email)

        return job

    async def run(
        self,
        filter_company: Optional[str] = None,
        max_companies: Optional[int] = None,
        verify_links: bool = True,
        enable_feeds: bool = True,
        max_roles_per_company: Optional[int] = DEFAULT_MAX_ROLES_PER_COMPANY,
        limit: int = DEFAULT_HARVEST_LIMIT,
        output_all_unreported: bool = True,
        include_discovered: bool = False,
        max_discovered: int = 100
    ) -> HarvestResult:
        # Reset internship funnel tracking for this run
        self.internship_funnel = {
            "seen": 0,
            "dropped_onsite": 0,
            "dropped_us_only": 0,
            "dropped_stale": 0,
            "dropped_low_score": 0,
            "kept": 0
        }

        companies = self.load_companies(filter_company)
        if include_discovered and not filter_company:
            discovered_from_db = get_discovered_companies(limit=max_discovered)
            if discovered_from_db:
                existing_keys = {(c.get("slug", "").lower(), c.get("ats", "").lower()) for c in companies}
                to_add = [d for d in discovered_from_db if (d.get("slug", "").lower(), d.get("ats", "").lower()) not in existing_keys]
                companies.extend(to_add)
                print(f"[*] Added {len(to_add)} auto-discovered companies from SQLite for scanning.")

        if max_companies:
            companies = companies[:max_companies]

        # Seed companies into SQLite catalog
        upsert_companies(companies)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        total_scanned = 0
        raw_company_jobs: Dict[str, List[JobRequisition]] = {}
        scanned_company_names = set(c.get("name", c.get("slug", "")) for c in companies)

        async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
            # 1. Fetch seed companies concurrently
            sem = asyncio.Semaphore(MAX_CONCURRENT_COMPANIES)

            async def fetch_bounded(comp: dict):
                comp_name = comp.get("name", comp.get("slug", ""))
                async with sem:
                    return comp_name, await self.fetch_company_jobs(client, comp)

            print(f"[*] Concurrently scanning {len(companies)} target companies (Concurrency: {MAX_CONCURRENT_COMPANIES})...")
            fetch_tasks = [fetch_bounded(c) for c in companies]
            fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            for item in fetch_results:
                if isinstance(item, tuple):
                    comp_name, jobs = item
                    raw_company_jobs[comp_name] = jobs
                    total_scanned += len(jobs)

            # 2. Ingest dynamic feeds (SimplifyJobs, HN Who Is Hiring, Remotive, Himalayas)
            feed_jobs: List[JobRequisition] = []
            if enable_feeds and not filter_company:
                print("[*] Ingesting live feeds (SimplifyJobs, HN Who Is Hiring, Remotive, Himalayas)...")
                feed_results = await asyncio.gather(
                    fetch_simplify_feed(client),
                    fetch_hn_feed(client),
                    fetch_remotive_jobs(client),
                    fetch_himalayas_jobs(client),
                    return_exceptions=True
                )
                discovered_comps = []
                for res in feed_results:
                    if isinstance(res, tuple):
                        f_jobs, f_comps = res
                        feed_jobs.extend(f_jobs)
                        total_scanned += len(f_jobs)
                        discovered_comps.extend(f_comps)

                # Persist discovered companies in SQLite (dedup by (slug, ats))
                if discovered_comps:
                    unique_comps = []
                    seen_comp_keys = set()
                    for c in discovered_comps:
                        ck = (c.get("slug", "").lower(), c.get("ats", "").lower())
                        if ck not in seen_comp_keys:
                            seen_comp_keys.add(ck)
                            unique_comps.append(c)
                    upsert_companies(unique_comps)
                    print(f"[*] Persisted {len(unique_comps)} newly discovered ATS company slugs into SQLite.")

                for fj in feed_jobs:
                    raw_company_jobs.setdefault(fj.company, []).append(fj)

            # 3. Filter and score all candidate jobs
            company_candidate_matches: Dict[str, List[JobRequisition]] = {}
            seen_apply_urls: set = set()
            for comp_name, jobs in raw_company_jobs.items():
                valid_jobs = []
                for j in jobs:
                    clean_url = j.apply_url.rstrip("/")
                    dedup_key = (j.company.lower().strip(), j.title.lower().strip(), clean_url)
                    if dedup_key in seen_apply_urls:
                        continue
                    scored_job = self.filter_and_score_job(j)
                    if scored_job:
                        seen_apply_urls.add(dedup_key)
                        valid_jobs.append(scored_job)
                if valid_jobs:
                    company_candidate_matches[comp_name] = valid_jobs

            # 4. Live Link Verification Gate (For raw external links)
            all_verified_jobs: List[JobRequisition] = []
            closed_companies: List[str] = []

            verify_sem = asyncio.Semaphore(MAX_CONCURRENT_COMPANIES)

            async def verify_one(job: JobRequisition) -> Optional[JobRequisition]:
                # If already verified via direct ATS JSON API or mailto, trust immediately
                if job.is_verified or job.apply_url.startswith("mailto:"):
                    return job
                async with verify_sem:
                    is_valid, _ = await verify_requisition_link(client, job.apply_url)
                    if is_valid:
                        job.is_verified = True
                        return job
                    return None

            # Track closed companies
            for comp_name in scanned_company_names:
                if not company_candidate_matches.get(comp_name):
                    closed_companies.append(comp_name)

            for comp_name, candidates in company_candidate_matches.items():
                if verify_links:
                    verify_tasks = [verify_one(j) for j in candidates]
                    verify_res = await asyncio.gather(*verify_tasks, return_exceptions=True)
                    verified = [r for r in verify_res if isinstance(r, JobRequisition)]
                else:
                    verified = candidates

                if verified:
                    # 5. Anti-Monopoly Guardrail: Sort by score descending and cap at max_roles_per_company
                    if max_roles_per_company and max_roles_per_company > 0:
                        verified.sort(key=lambda j: j.score, reverse=True)
                        verified = verified[:max_roles_per_company]
                    all_verified_jobs.extend(verified)
                else:
                    if comp_name in scanned_company_names:
                        closed_companies.append(comp_name)

        # 6. Stateful Persistence: Batch upsert jobs into SQLite
        stats = upsert_jobs(all_verified_jobs)
        print(f"[*] SQLite Sync: {stats['net_new']} net-new jobs inserted, {stats['updated']} jobs refreshed.")

        # 7. Select report positions (by default, report net-new/unreported roles; sort by score descending)
        all_verified_jobs.sort(key=lambda j: j.score, reverse=True)
        if output_all_unreported:
            all_ids = [j.id for j in all_verified_jobs]
            unreported_ids = get_unreported_job_ids(all_ids)
            report_jobs = [j for j in all_verified_jobs if j.id in unreported_ids]
        else:
            report_jobs = all_verified_jobs

        if limit and limit > 0:
            report_jobs = report_jobs[:limit]

        # Mark reported jobs in SQLite
        mark_jobs_reported([j.id for j in report_jobs])

        funnel = self.internship_funnel
        print(
            f"[*] Internship Funnel: Seen: {funnel['seen']} | "
            f"Dropped On-site: {funnel['dropped_onsite']} | "
            f"Dropped Geo/Auth: {funnel['dropped_us_only']} | "
            f"Dropped Stale (>90d): {funnel['dropped_stale']} | "
            f"Dropped Low Score (<35): {funnel['dropped_low_score']} | "
            f"Kept: {funnel['kept']}"
        )

        today_str = datetime.now().strftime("%Y-%m-%d")
        return HarvestResult(
            date_str=today_str,
            active_jobs=report_jobs,
            closed_companies=sorted(closed_companies),
            total_scanned=total_scanned,
            net_new_count=stats["net_new"],
            internship_funnel=dict(self.internship_funnel)
        )
