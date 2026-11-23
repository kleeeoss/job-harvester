import pytest
from datetime import datetime, timezone, timedelta
from engine.analyzer.eligibility import check_eligibility, has_cgpa_cutoff, is_posting_fresh

def test_reject_us_citizenship_and_security_clearance():
    text = "We are seeking a Backend Engineer. Must be a US Citizen only with active DoD Secret security clearance."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert not eligible
    assert "clearance" in reason.lower() or "citizenship" in reason.lower()

def test_reject_us_residency_requirement():
    text = "Go Developer. Remote role, but applicant must reside in the US and hold US work authorization (no C2C)."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert not eligible
    assert "us" in reason.lower() or "authorization" in reason.lower()

def test_accept_high_cgpa_cutoff_per_user_preference():
    text = "Campus hiring: Requires minimum 8.0 CGPA or 80% aggregate across all semesters."
    eligible, reason = check_eligibility(text, is_internship=True)
    # CGPA cutoff is no longer hard-dropped
    assert eligible
    assert reason == "Eligible"
    # But it is detected for the -5 soft penalty
    assert has_cgpa_cutoff(text)

def test_accept_past_graduation_batch_per_user_preference():
    text = "Internship opportunity for 2024 and 2025 batch graduates only. Final year students ready to join immediately."
    eligible, reason = check_eligibility(text, is_internship=True)
    # Graduation batch is no longer hard-dropped
    assert eligible
    assert reason == "Eligible"

def test_accept_generic_unrestricted_role():
    text = "Software Engineer - Infrastructure. Working on distributed container runtimes with Go and Kubernetes."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert eligible
    assert reason == "Eligible"

def test_reject_senior_titles_and_high_experience_in_eligibility():
    text = "Join our backend team. Requires minimum 8 years of professional software engineering experience."
    eligible, reason = check_eligibility(text, is_internship=False, role_title="Staff Engineer")
    assert not eligible
    assert "senior" in reason.lower() or "lead" in reason.lower() or "experience" in reason.lower()

def test_reject_3_plus_years_experience():
    text = "We are hiring an engineer. Must have at least 3+ years of professional production experience in Go."
    eligible, reason = check_eligibility(text, is_internship=False, role_title="Software Engineer")
    assert not eligible
    assert "experience" in reason.lower()

def test_freshness_cutoff_within_30_days():
    recent_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    fresh, msg = is_posting_fresh(recent_date)
    assert fresh
    assert "fresh" in msg.lower()

def test_freshness_cutoff_exceeding_30_days():
    stale_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    fresh, msg = is_posting_fresh(stale_date)
    assert not fresh
    assert "stale" in msg.lower()

def test_reject_non_engineering_roles():
    from engine.harvester import is_engineering_role
    assert not is_engineering_role("Marketing internship (brand & communication)")
    assert not is_engineering_role("Product User Research, Intern")
    assert not is_engineering_role("Product Manager – Media & Entertainment")
    assert not is_engineering_role("Talent Partner / Recruiter")
    assert not is_engineering_role("Engineering Manager, Software Engineering")
    assert not is_engineering_role("Senior Manager, Software Engineering")
    assert not is_engineering_role("Staff Machine Learning Manager")
    assert not is_engineering_role("Staff Engineer - Infrastructure")
    assert not is_engineering_role("Principal Software Engineer")
    assert not is_engineering_role("SDE III - Devops")
    assert not is_engineering_role("Senior Software Engineer - Backend")
    assert is_engineering_role("Systems Engineering Intern")
    assert is_engineering_role("Software Development Engineer")
    assert is_engineering_role("Member of Technical Staff - SDK")
    assert is_engineering_role("Backend Engineer")

def test_hard_exclude_sde2_field_devrel_qa():
    from engine.analyzer.eligibility import is_engineering_role
    excluded_titles = [
        "SDE2 - API Platform",
        "SDE-2 - Backend",
        "SDE II - Infrastructure",
        "Software Engineer II",
        "Backend Developer 2",
        "Intermediate Software Engineer",
        "Field Engineer, Life Sciences",
        "Field Engineer, Healthcare",
        "Developer Relations Engineer",
        "DevRel Advocate",
        "QA Engineer - Automation",
        "Quality Assurance Engineer",
        "Technical Account Engineer",
        "Professional Services Engineer - KSA",
        "Technical Services Engineer",
        "Software Development Engineer in Test - SDET",
        "SDET",
        "Software Engineer in Test",
        "Quality Engineer in Test"
    ]
    for title in excluded_titles:
        assert not is_engineering_role(title), f"Expected '{title}' to be rejected, but it passed"

def test_parse_numeric_unix_epoch_string():
    from engine.analyzer.eligibility import parse_posting_date
    from datetime import datetime, timezone

    # 1. Epoch seconds as numeric string (e.g. from Himalayas)
    dt_sec = parse_posting_date("1700000000")
    assert dt_sec is not None
    assert dt_sec.tzinfo == timezone.utc
    assert dt_sec.year == 2023

    # 2. Epoch milliseconds as numeric string (e.g. from Lever or Simplify)
    dt_ms = parse_posting_date("1700000000000")
    assert dt_ms is not None
    assert dt_ms.tzinfo == timezone.utc
    assert dt_ms.year == 2023

def test_direct_ats_freshness_120_days():
    from engine.analyzer.eligibility import check_eligibility
    from datetime import datetime, timezone, timedelta

    # Posting from 60 days ago
    sixty_days_ago = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()

    # Raw feed (is_direct_ats=False): must be rejected (exceeds 30-day cutoff)
    valid_raw, reason_raw = check_eligibility(
        "Software Engineer role",
        is_internship=False,
        role_title="Software Engineer",
        posted_date=sixty_days_ago,
        is_direct_ats=False
    )
    assert not valid_raw
    assert "stale" in reason_raw.lower()

    # Direct ATS API (is_direct_ats=True): must be ACCEPTED (within 120-day cutoff for evergreen roles)
    valid_ats, reason_ats = check_eligibility(
        "Software Engineer role",
        is_internship=False,
        role_title="Software Engineer",
        posted_date=sixty_days_ago,
        is_direct_ats=True
    )
    assert valid_ats
    assert reason_ats == "Eligible"

