import pytest
from engine.analyzer.compensation import parse_compensation, PayTier

def test_reject_unpaid_internship():
    text = "Join us as a Software Engineering Intern. This is an unpaid internship for college credit."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert not valid
    assert "unpaid" in reason.lower()

def test_reject_sub_10k_internship():
    text = "Backend Intern wanted. Stipend: INR 8,000 per month."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert not valid
    assert "below" in reason.lower()

def test_tier_internship_10k_to_20k():
    text = "Systems Intern. Stipend is ₹15,000 / month."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_10K_20K
    assert "15,000" in comp_str

def test_tier_internship_20k_to_30k():
    text = "Cloud Infrastructure Intern. Monthly stipend: 25,000 INR pm."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_20K_30K
    assert "25,000" in comp_str

def test_tier_internship_30k_to_40k():
    text = "AI/ML Engineering Intern. Stipend: ₹35,000/month."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_30K_40K
    assert "35,000" in comp_str

def test_tier_internship_40k_to_50k():
    text = "Distributed Systems Intern. Stipend: ₹45,000/month."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_40K_50K
    assert "45,000" in comp_str

def test_unlisted_stipend_venture_backed():
    text = "Software Engineering Intern at high growth AI startup. Competitive stipend."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_UNLISTED
    assert "unlisted" in comp_str.lower() or "venture-backed" in comp_str.lower()

def test_reject_sub_10_lpa_job():
    text = "Junior Backend Developer. Salary range: 5 to 7 LPA based on performance."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert not valid
    assert "below" in reason.lower()

def test_tier_job_10_to_15_lpa():
    text = "Software Engineer - Golang. CTC: 12 - 14 LPA + ESOPs."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_10_15_LPA
    assert "12" in comp_str

def test_tier_job_15_to_30_lpa():
    text = "Distributed Systems Engineer. Compensation: 22 - 28 LPA."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_15_30_LPA
    assert "22" in comp_str

def test_tier_job_30_to_45_lpa():
    text = "Cloud Infrastructure Engineer. Salary: 35 - 40 LPA."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_30_45_LPA
    assert "35" in comp_str

def test_tier_job_45_to_60_lpa():
    text = "Senior Cloud Architect. Base pay 45 LPA to 55 LPA."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_45_60_LPA
    assert "45" in comp_str

def test_unlisted_salary_venture_backed():
    text = "Software Engineer at Series A AI startup. Competitive equity package and market salary."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_UNLISTED
    assert "unlisted" in comp_str.lower() or "venture-backed" in comp_str.lower()

def test_tier_internship_k_notation():
    text = "Software Engineering Intern. Stipend: 25k/month for 6 months."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_20K_30K
    assert "25,000" in comp_str

def test_tier_internship_k_notation_35k():
    text = "Backend Systems Intern. Stipend is 35k pm."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=True)
    assert valid
    assert tier == PayTier.INTERN_30K_40K
    assert "35,000" in comp_str

def test_tier_job_usd_annual_full():
    text = "Full Stack Engineer. Base salary: $120,000 - $150,000 / year."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_45_60_LPA
    assert "120,000" in comp_str

def test_tier_job_hourly_rate():
    text = "Systems Developer. Pay is $50/hr for full time work."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_45_60_LPA
    assert "50" in comp_str

def test_tier_job_lakhs_notation():
    text = "Software Engineer. Compensation: 16 - 20 Lakhs per annum."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_15_30_LPA
    assert "16" in comp_str

def test_ignore_funding_round_numbers():
    text = "We just raised a $500k seed round and are hiring our founding software engineer."
    valid, tier, comp_str, reason = parse_compensation(text, is_internship=False)
    assert valid
    assert tier == PayTier.JOB_UNLISTED
    assert "unlisted" in comp_str.lower()
