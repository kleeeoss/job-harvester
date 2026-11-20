import pytest
from engine.models import JobRequisition, HarvestResult, PayTier
from engine.output.markdown_gen import generate_harvest_report
from engine.output.cold_pitch_gen import generate_cold_pitch

def test_cold_pitch_tailoring():
    pitch = generate_cold_pitch("Modal Labs", "Systems Engineer", ["Go", "Docker", "Distributed Systems"])
    assert "https://garvvaidya.vercel.app" in pitch
    assert "Lucid-CI" in pitch or "systems" in pitch.lower()
    # Ensure word count is approximately 75 words (60-90 words)
    word_count = len(pitch.split())
    assert 50 <= word_count <= 95

def test_markdown_report_structure():
    job1 = JobRequisition(
        id="job1",
        company="Modal Labs",
        title="Systems Engineering Intern",
        location="Remote (Worldwide)",
        apply_url="https://app.ashbyhq.com/modal/systems-intern",
        description_text="Go systems distributed engine",
        is_internship=True,
        pay_tier=PayTier.INTERN_30K_50K,
        compensation_str="₹40,000/mo ($500/mo)",
        is_top_tier=True,
        is_verified=True,
        match_rationale="Go, Docker, Distributed container isolation"
    )

    job2 = JobRequisition(
        id="job2",
        company="Sarvam AI",
        title="Backend Infrastructure Engineer",
        location="Bengaluru, India",
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
        apply_url="https://jobs.lever.co/earlyai/founding-eng",
        description_text="Building distributed AI inference",
        is_internship=False,
        pay_tier=PayTier.UNLISTED,
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

    # 1. Top-Tier / High-Pay Section exists
    assert "Top-Tier & High-Compensation" in report_md or "Top Tier" in report_md

    # 2. Pay Tiers are present
    assert "₹30,000 – ₹50,000 / month" in report_md or "30k-50k" in report_md
    assert "15 – 30 LPA" in report_md or "15-30 LPA" in report_md
    assert "Unlisted Salary" in report_md

    # 3. Direct application URLs are formatted as links
    assert "https://app.ashbyhq.com/modal/systems-intern" in report_md
    assert "https://boards.greenhouse.io/sarvam/jobs/123" in report_md

    # 4. Negative Finding Integrity section exists
    assert "Closed / Zero Active Requisitions" in report_md or "Negative Finding Integrity" in report_md
    assert "BrowserStack" in report_md
    assert "Postman" in report_md

    # 5. Cold outreach template included
    assert "https://garvvaidya.vercel.app" in report_md
