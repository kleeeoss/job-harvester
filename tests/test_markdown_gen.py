import pytest
from engine.models import JobRequisition, HarvestResult, PayTier
from engine.output.markdown_gen import generate_harvest_report

def test_markdown_report_structure():
    job1 = JobRequisition(
        id="job1",
        company="Modal Labs",
        title="Systems Engineering Intern",
        location="Worldwide Remote",
        location_type="Worldwide Remote",
        apply_url="https://app.ashbyhq.com/modal/systems-intern",
        description_text="Go systems distributed engine",
        is_internship=True,
        pay_tier=PayTier.INTERN_40K_50K,
        compensation_str="₹45,000/mo ($550/mo)",
        is_top_tier=True,
        is_verified=True,
        match_rationale="Go, Docker, Distributed container isolation"
    )

    job2 = JobRequisition(
        id="job2",
        company="Sarvam AI",
        title="Backend Infrastructure Engineer",
        location="Bengaluru, India",
        location_type="India (On-site/Hybrid)",
        apply_url="https://boards.greenhouse.io/sarvam/jobs/123",
        description_text="Python high throughput backend",
        is_internship=False,
        pay_tier=PayTier.JOB_15_30_LPA,
        compensation_str="20 - 25 LPA",
        is_top_tier=True,
        is_verified=True,
        match_rationale="Python, AWS, high-throughput microservices"
    )

    job3 = JobRequisition(
        id="job3",
        company="EarlyAI",
        title="Founding Systems Engineer",
        location="Remote, India",
        location_type="India (Remote)",
        apply_url="https://jobs.lever.co/earlyai/founding-eng",
        description_text="Building distributed AI inference",
        is_internship=False,
        pay_tier=PayTier.JOB_UNLISTED,
        compensation_str="[Unlisted Salary: Venture-Backed Competitive]",
        is_top_tier=False,
        is_verified=True,
        match_rationale="Distributed Systems, Go, Docker"
    )

    result = HarvestResult(
        date_str="2026-11-20",
        active_jobs=[job1, job2, job3],
        closed_companies=["BrowserStack", "Postman"],
        total_scanned=25
    )

    report_md = generate_harvest_report(result)

    # 1. Part 1 (Internships) exists and contains intern role
    assert "Part 1: Internships" in report_md
    assert "₹40,000 – ₹50,000 / month" in report_md
    assert "Modal Labs" in report_md
    assert "Systems Engineering Intern" in report_md

    # 2. Part 2 (Full-Time Jobs) exists and contains full-time roles
    assert "Part 2: Full-Time Engineering Jobs" in report_md
    assert "15 – 30 LPA" in report_md
    assert "Sarvam AI" in report_md
    assert "Backend Infrastructure Engineer" in report_md

    # 3. Location column explicitly highlights Remote vs On-site
    assert "India (On-site/Hybrid)" in report_md
    assert "Worldwide Remote" in report_md

    # 4. Direct application URLs are formatted as links
    assert "https://app.ashbyhq.com/modal/systems-intern" in report_md
    assert "https://boards.greenhouse.io/sarvam/jobs/123" in report_md

    # 5. Negative Finding Audit section exists
    assert "Negative Finding Audit" in report_md
    assert "BrowserStack" in report_md
    assert "Postman" in report_md

    # 6. CRITICAL: Completely purged of cold pitch and outreach messages
    assert "Section 3" not in report_md
    assert "cold pitch" not in report_md.lower()
    assert "outreach messages" not in report_md.lower()
    assert "founder cold outreach" not in report_md.lower()

def test_markdown_report_hn_permalink_and_funnel_summary():
    founder_job = JobRequisition(
        id="hn_founder_1",
        company="Kernel AI",
        title="Founding Systems Intern",
        location="Worldwide Remote",
        location_type="Worldwide Remote",
        apply_url="mailto:founder@kernel.ai",
        contact_email="founder@kernel.ai",
        hn_permalink="https://news.ycombinator.com/item?id=42000000",
        description_text="Go systems distributed engine",
        is_internship=True,
        pay_tier=PayTier.INTERN_UNLISTED,
        compensation_str="[Unlisted Stipend: Venture-Backed Competitive]",
        is_top_tier=True,
        is_verified=True,
        match_rationale="Go, Docker, Distributed container isolation",
        ats="DIRECT_FOUNDER_EMAIL"
    )

    result = HarvestResult(
        date_str="2026-11-23",
        active_jobs=[founder_job],
        closed_companies=["Supabase"],
        total_scanned=10,
        net_new_count=1,
        internship_funnel={
            "seen": 15,
            "dropped_onsite": 4,
            "dropped_us_only": 6,
            "dropped_stale": 2,
            "dropped_low_score": 2,
            "kept": 1
        }
    )

    report_md = generate_harvest_report(result)

    # 1. Check founder email and HN permalink formatting
    assert "[📧 Email Founder (founder@kernel.ai)](mailto:founder@kernel.ai) • [HN Post](https://news.ycombinator.com/item?id=42000000)" in report_md

    # 2. Check 45+ LPA / Global USD header
    assert "Full-Time: 45+ LPA / Global USD" in report_md

    # 3. Check 0 MATCHING ROLES in negative finding audit
    assert "0 MATCHING ROLES" in report_md

    # 4. Check Internship Funnel summary line
    assert "Internship Funnel:** Seen: 15 | Dropped On-site: 4 | Dropped Geo/Auth: 6 | Dropped Stale (>90d): 2 | Dropped Low Score (<35): 2 | Kept: 1" in report_md

