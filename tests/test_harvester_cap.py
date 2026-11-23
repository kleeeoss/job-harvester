import pytest
import asyncio
from engine.models import JobRequisition, PayTier
from engine.harvester import JobHarvester
from engine.analyzer.geo_filter import check_location

def test_anti_monopoly_cap_and_tech_ranking():
    harvester = JobHarvester()

    # Create 8 jobs for "Acme Corp" with different tech scores
    jobs = []
    for score in [10, 80, 30, 95, 50, 40, 90, 20]:
        job = JobRequisition(
            id=f"job_{score}",
            company="Acme Corp",
            title=f"Engineer {score}",
            location="Bengaluru, India",
            location_type="India (On-site/Hybrid)",
            apply_url=f"https://boards.greenhouse.io/acme/{score}",
            description_text="Software engineer",
            is_internship=False,
            pay_tier=PayTier.JOB_15_30_LPA,
            tech_score=score,
            is_verified=True
        )
        jobs.append(job)

    # Mock raw company jobs
    harvester.load_companies = lambda filter_company=None: [{"name": "Acme Corp", "slug": "acme", "ats": "greenhouse"}]
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=jobs)
    harvester.filter_and_score_job = lambda j: j

    # Run with default cap of 3
    result = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            max_roles_per_company=3,
            output_all_unreported=False
        )
    )

    assert len(result.active_jobs) == 3
    # The selected 3 must have scores 95, 90, 80 (highest tech scores)
    scores = [j.tech_score for j in result.active_jobs]
    assert scores == [95, 90, 80]

def test_no_cap_allows_all_jobs():
    harvester = JobHarvester()

    jobs = [
        JobRequisition(
            id=f"job_{i}",
            company="Mega Corp",
            title=f"Engineer {i}",
            location="Worldwide Remote",
            location_type="Worldwide Remote",
            apply_url=f"https://jobs.ashbyhq.com/megacorp/{i}",
            description_text="Systems engineer",
            is_internship=False,
            pay_tier=PayTier.JOB_30_45_LPA,
            tech_score=50 + i,
            is_verified=True
        )
        for i in range(10)
    ]

    harvester.load_companies = lambda filter_company=None: [{"name": "Mega Corp", "slug": "megacorp", "ats": "ashby"}]
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=jobs)
    harvester.filter_and_score_job = lambda j: j

    # Run with no cap
    result = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            max_roles_per_company=None,
            output_all_unreported=False
        )
    )

    assert len(result.active_jobs) == 10

def test_internship_strictly_remote_enforcement():
    # India on-site internship must be rejected
    is_valid, loc_type, reason = check_location("Bengaluru, India", "", is_internship=True)
    assert not is_valid
    assert "strictly 100% remote" in reason.lower()

    # India remote internship must be accepted
    is_valid_remote, loc_type_remote, _ = check_location("Remote, India", "", is_internship=True)
    assert is_valid_remote
    assert loc_type_remote == "India (Remote)"

    # Full-time job in Bengaluru on-site must be accepted
    is_valid_ft, loc_type_ft, _ = check_location("Bengaluru, India", "", is_internship=False)
    assert is_valid_ft
    assert "On-site" in loc_type_ft

def test_harvest_output_limit():
    harvester = JobHarvester()

    jobs = [
        JobRequisition(
            id=f"job_{i}",
            company=f"Company {i}",
            title="Software Engineer",
            location="Remote",
            location_type="Worldwide Remote",
            apply_url=f"https://jobs.ashbyhq.com/c/{i}",
            description_text="Go systems",
            is_internship=False,
            pay_tier=PayTier.JOB_15_30_LPA,
            tech_score=80,
            is_verified=True
        )
        for i in range(20)
    ]

    companies = [{"name": f"Company {i}", "slug": f"c_{i}", "ats": "ashby"} for i in range(20)]
    harvester.load_companies = lambda filter_company=None: companies
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=[
        j for j in jobs if j.company == comp["name"]
    ])
    harvester.filter_and_score_job = lambda j: j

    result = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            max_roles_per_company=1,
            limit=5,
            output_all_unreported=False
        )
    )

    assert len(result.active_jobs) == 5

def test_feed_jobs_from_new_companies_are_included():
    harvester = JobHarvester()

    # Seed company with 0 jobs
    harvester.load_companies = lambda filter_company=None: [{"name": "SeedCo", "slug": "seedco", "ats": "ashby"}]
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=[])

    # Feed returns job from a new company "FeedCo"
    feed_job = JobRequisition(
        id="feed_1",
        company="FeedCo",
        title="Software Engineer - Systems",
        location="Worldwide Remote",
        location_type="Worldwide Remote",
        apply_url="https://jobs.ashbyhq.com/feedco/feed_1",
        description_text="Go systems container infrastructure",
        is_internship=False,
        pay_tier=PayTier.JOB_30_45_LPA,
        tech_score=90,
        is_verified=True
    )

    import engine.harvester
    engine.harvester.fetch_simplify_feed = lambda client: asyncio.sleep(0, result=([feed_job], [{"name": "FeedCo", "slug": "feedco", "ats": "ashby"}]))
    engine.harvester.fetch_hn_feed = lambda client: asyncio.sleep(0, result=([], []))
    engine.harvester.fetch_remotive_jobs = lambda client: asyncio.sleep(0, result=([], []))
    engine.harvester.fetch_himalayas_jobs = lambda client: asyncio.sleep(0, result=([], []))

    result = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=True,
            max_roles_per_company=3,
            output_all_unreported=False
        )
    )

    # FeedCo job must be included in active_jobs!
    assert len(result.active_jobs) == 1
    assert result.active_jobs[0].company == "FeedCo"
    # SeedCo must be reported in closed_companies
    assert "SeedCo" in result.closed_companies

def test_reject_non_engineering_titles():
    from engine.harvester import is_engineering_role
    assert not is_engineering_role("AI Deployment Strategist")
    assert not is_engineering_role("People Systems Engineer")
    assert not is_engineering_role("IT Systems Engineer")
    assert not is_engineering_role("IT Engineer")
    assert not is_engineering_role("Systems Engineer II - R&D Business Systems")
    assert not is_engineering_role("Solutions Engineer, Florida (Enterprise)")
    assert is_engineering_role("AI Infrastructure System Engineer")
    assert is_engineering_role("Software Engineer - Systems")
    assert is_engineering_role("Backend Infrastructure Engineer")
    assert is_engineering_role("Systems Engineering Intern")

def test_internship_funnel_tracking():
    harvester = JobHarvester()

    # 1. On-site intern
    j_onsite = JobRequisition(
        id="j_on", company="CoA", title="Software Engineering Intern",
        location="Bengaluru, India", apply_url="https://jobs.ashbyhq.com/coa/1",
        description_text="Python intern", is_internship=True
    )
    # 2. US restricted intern
    j_us = JobRequisition(
        id="j_us", company="CoB", title="Software Engineering Intern",
        location="San Francisco, CA (US only)", apply_url="https://jobs.ashbyhq.com/cob/2",
        description_text="Python intern", is_internship=True
    )
    # 3. Stale intern (> 90 days)
    j_stale = JobRequisition(
        id="j_stale", company="CoC", title="Software Engineering Intern",
        location="Remote", apply_url="https://jobs.ashbyhq.com/coc/3",
        description_text="Python intern", is_internship=True, posted_date="2024-01-01T00:00:00Z"
    )
    # 4. Valid remote intern with low score (< 35)
    j_low = JobRequisition(
        id="j_low", company="CoD", title="Sales Support Intern", # non engineering or minimal stack
        location="Remote", apply_url="https://jobs.ashbyhq.com/cod/4",
        description_text="Minimal text", is_internship=True
    )
    # 5. Kept intern (Go, Docker, Remote)
    j_kept = JobRequisition(
        id="j_kept", company="CoE", title="Systems Software Intern",
        location="Worldwide Remote", apply_url="https://jobs.ashbyhq.com/coe/5",
        description_text="Go systems Docker gVisor Kubernetes Terraform", is_internship=True
    )

    harvester.filter_and_score_job(j_onsite)
    harvester.filter_and_score_job(j_us)
    harvester.filter_and_score_job(j_stale)
    harvester.filter_and_score_job(j_low)
    kept_res = harvester.filter_and_score_job(j_kept)

    assert kept_res is not None
    assert harvester.internship_funnel["seen"] >= 4
    assert harvester.internship_funnel["dropped_onsite"] >= 1
    assert harvester.internship_funnel["dropped_us_only"] >= 1
    assert harvester.internship_funnel["dropped_stale"] >= 1
    assert harvester.internship_funnel["kept"] >= 1

def test_ashby_structured_pay_tier_preservation():
    harvester = JobHarvester()
    job = JobRequisition(
        id="ashby_comp_1",
        company="Modal Labs",
        title="Software Engineer Intern",
        location="Worldwide Remote",
        location_type="Worldwide Remote",
        apply_url="https://jobs.ashbyhq.com/modal/1",
        description_text="Join our team working on Go and Python container runtime systems. No salary mentioned in text.",
        is_internship=True,
        pay_tier=PayTier.INTERN_20K_30K,
        compensation_str="₹25,000/mo ($300/mo)"
    )

    scored = harvester.filter_and_score_job(job)
    assert scored is not None
    # Must preserve the structured pay tier and NOT overwrite with INTERN_UNLISTED
    assert scored.pay_tier == PayTier.INTERN_20K_30K
    assert scored.compensation_str == "₹25,000/mo ($300/mo)"

def test_mailto_and_hn_role_dedup_by_company_title_url():
    harvester = JobHarvester()

    role1 = JobRequisition(
        id="hn_role_dedup_1", company="Kernel AI", title="Systems Engineer",
        location="Remote", apply_url="mailto:founder@kernel.ai",
        description_text="Go Kubernetes systems", tech_score=80, is_verified=True
    )
    role2 = JobRequisition(
        id="hn_role_dedup_2", company="Kernel AI", title="Systems Intern",
        location="Remote", apply_url="mailto:founder@kernel.ai",
        description_text="Go systems intern", is_internship=True, tech_score=75, is_verified=True
    )

    harvester.load_companies = lambda filter_company=None: [{"name": "Kernel AI", "slug": "kernel", "ats": "hn"}]
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=[role1, role2])
    harvester.filter_and_score_job = lambda j: j

    res = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            max_roles_per_company=5,
            output_all_unreported=False
        )
    )

    # Both roles share the mailto URL but have different titles; both must be kept!
    assert len(res.active_jobs) == 2
    titles = {j.title for j in res.active_jobs}
    assert titles == {"Systems Engineer", "Systems Intern"}

def test_output_all_unreported_filtering():
    import uuid
    harvester = JobHarvester()

    job_id = f"test_unreported_{uuid.uuid4().hex[:8]}"
    role = JobRequisition(
        id=job_id, company="AsyncAI", title="Cloud Engineer",
        location="Worldwide Remote", apply_url=f"https://jobs.ashbyhq.com/asyncai/{job_id}",
        description_text="Go systems", tech_score=85, is_verified=True
    )

    harvester.load_companies = lambda filter_company=None: [{"name": "AsyncAI", "slug": "asyncai", "ats": "ashby"}]
    harvester.fetch_company_jobs = lambda client, comp: asyncio.sleep(0, result=[role])
    harvester.filter_and_score_job = lambda j: j

    # First run with output_all_unreported=True: job is unreported, so it must be returned!
    res1 = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            output_all_unreported=True
        )
    )
    assert any(j.id == job_id for j in res1.active_jobs)

    # Second run with output_all_unreported=True: job was marked reported in res1, so it must be omitted!
    res2 = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            output_all_unreported=True
        )
    )
    assert not any(j.id == job_id for j in res2.active_jobs)

    # Third run with output_all_unreported=False (--all): job must be returned even if previously reported!
    res3 = asyncio.run(
        harvester.run(
            verify_links=False,
            enable_feeds=False,
            output_all_unreported=False
        )
    )
    assert any(j.id == job_id for j in res3.active_jobs)


