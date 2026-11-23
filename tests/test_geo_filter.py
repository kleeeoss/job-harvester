import pytest
from engine.analyzer.geo_filter import evaluate_geo_and_auth

def test_hard_drop_us_only_location():
    eligible, loc_type, reason, points = evaluate_geo_and_auth("San Francisco, CA (US Only)")
    assert not eligible
    assert "us" in reason.lower() or "restricted" in reason.lower()

def test_hard_drop_us_residency_requirement_in_text():
    eligible, loc_type, reason, points = evaluate_geo_and_auth(
        "Remote",
        job_text="Backend Go Engineer. Candidate must reside in the US and be authorized to work on W2 (no C2C)."
    )
    assert not eligible
    assert "us" in reason.lower() or "restricted" in reason.lower()

def test_keep_and_boost_india_remote():
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Bengaluru, Karnataka (Remote)")
    assert eligible
    assert loc_type == "India (Remote)"
    assert points >= 18

def test_keep_india_onsite_for_jobs():
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Hyderabad, Telangana", is_internship=False)
    assert eligible
    assert loc_type == "India (On-site/Hybrid)"
    assert points >= 15

def test_reject_india_onsite_for_internships():
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Pune, India (In-Office)", is_internship=True)
    assert not eligible
    assert "strictly 100% remote" in reason.lower()

def test_keep_and_boost_worldwide_remote():
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Remote (Worldwide / Global)")
    assert eligible
    assert loc_type == "Worldwide Remote"
    assert points >= 20

def test_legal_footer_immunity_for_global_remote():
    # Patch 5: When location is Worldwide Remote, US legal footer does not hard-drop
    desc = "We build distributed systems. Note: We cannot sponsor US work visas for this role."
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Worldwide Remote", job_text=desc)
    assert eligible
    assert loc_type == "Worldwide Remote"

def test_legal_footer_immunity_for_india_roles():
    # Patch 5: When location is India, boilerplate US sponsorship refusal does not hard-drop
    desc = "Engineering role in Bengaluru. Equal Opportunity Employer. We will not sponsor employment visas."
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Bengaluru, India", job_text=desc)
    assert eligible
    assert "India" in loc_type

def test_remote_hybrid_cloud_text_immunity():
    # "hybrid cloud" or "hybrid search" in text should NOT cause a 100% remote job to be rejected as Foreign Hybrid
    desc = "We deploy distributed workloads across hybrid cloud environments using hybrid search."
    eligible, loc_type, reason, points = evaluate_geo_and_auth("Worldwide Remote", job_text=desc)
    assert eligible, f"Rejected unexpectedly: {reason}"
    assert loc_type == "Worldwide Remote"

    # But explicit "hybrid work" in description should be detected
    desc_hybrid = "Software Engineer. This is a hybrid role requiring 3 days in office."
    el_h, loc_h, reason_h, _ = evaluate_geo_and_auth("Remote", job_text=desc_hybrid)
    assert not el_h
    assert "hybrid" in loc_h.lower() or "hybrid" in reason_h.lower()

def test_reject_foreign_regional_eea_and_uk_only():
    # Explicit rejection of EEA, EU only, EMEA only, UK only, LATAM only
    for loc in ["REMOTE (EEA)", "Remote (EU Only)", "Remote (EMEA only)", "Remote - UK only", "Remote - LATAM only"]:
        eligible, loc_type, reason, _ = evaluate_geo_and_auth(loc)
        assert not eligible, f"Expected {loc} to be rejected, but got eligible={eligible}"
        assert "restricted" in loc_type.lower() or "restricted" in reason.lower() or "foreign" in reason.lower()
