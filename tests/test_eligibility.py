import pytest
from engine.analyzer.eligibility import check_eligibility

def test_reject_us_citizenship_and_security_clearance():
    text = "We are seeking a Backend Engineer. Must be a US Citizen only with active DoD Secret security clearance."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert not eligible
    assert "clearance" in reason.lower() or "citizenship" in reason.lower()

def test_reject_us_residency_requirement():
    text = "Senior Go Developer. Remote role, but applicant must reside in the US and hold US work authorization (no C2C)."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert not eligible
    assert "us" in reason.lower() or "authorization" in reason.lower()

def test_reject_high_cgpa_cutoff():
    text = "Campus hiring: Requires minimum 8.0 CGPA or 80% aggregate across all semesters."
    eligible, reason = check_eligibility(text, is_internship=True)
    assert not eligible
    assert "cgpa" in reason.lower() or "gpa" in reason.lower()

def test_accept_safe_cgpa_cutoff():
    text = "Eligibility criteria: B.Tech in CSE/IT with minimum 6.5 CGPA or 65% aggregate."
    eligible, reason = check_eligibility(text, is_internship=True)
    assert eligible
    assert reason == "Eligible"

def test_reject_strict_past_graduation_batch_for_internship():
    text = "Internship opportunity for 2024 and 2025 batch graduates only. Final year students ready to join immediately."
    eligible, reason = check_eligibility(text, is_internship=True)
    assert not eligible
    assert "batch" in reason.lower()

def test_accept_2027_and_penultimate_batch():
    text = "Systems Engineering Intern. Open to pre-final year / penultimate year undergraduate students (Class of 2027)."
    eligible, reason = check_eligibility(text, is_internship=True)
    assert eligible
    assert reason == "Eligible"

def test_accept_generic_unrestricted_role():
    text = "Software Engineer - Infrastructure. Working on distributed container runtimes with Go and Kubernetes."
    eligible, reason = check_eligibility(text, is_internship=False)
    assert eligible
    assert reason == "Eligible"

def test_reject_non_engineering_roles():
    from engine.harvester import is_engineering_role
    assert not is_engineering_role("Marketing internship (brand & communication)")
    assert not is_engineering_role("Product User Research, Intern")
    assert not is_engineering_role("Product Manager – Media & Entertainment")
    assert not is_engineering_role("Talent Partner / Recruiter")
    assert is_engineering_role("Systems Engineering Intern")
    assert is_engineering_role("Software Development Engineer")
    assert is_engineering_role("Member of Technical Staff - SDK")

