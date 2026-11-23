import pytest
from engine.sources.simplify_feed import parse_simplify_item
from engine.sources.hn_feed import parse_hn_comment

def test_parse_simplify_active_item():
    item = {
        "active": True,
        "company_name": "Resend",
        "title": "Systems Engineering Intern",
        "url": "https://jobs.ashbyhq.com/resend/12345",
        "locations": ["Remote", "Worldwide"],
        "degrees": ["Bachelor's"]
    }
    job, comp = parse_simplify_item(item)
    assert job is not None
    assert job.company == "Resend"
    assert job.title == "Systems Engineering Intern"
    assert job.is_internship is True
    assert job.ats == "Ashby"
    assert "Remote" in job.location

    assert comp is not None
    assert comp["slug"] == "resend"
    assert comp["ats"] == "ashby"

def test_parse_simplify_inactive_item():
    item = {
        "active": False,
        "company_name": "Stripe",
        "title": "Software Engineer",
        "url": "https://boards.greenhouse.io/stripe/jobs/999"
    }
    job, comp = parse_simplify_item(item)
    assert job is None
    assert comp is None

def test_parse_simplify_missing_url():
    item = {
        "active": True,
        "company_name": "Stripe",
        "title": "Software Engineer",
        "url": ""
    }
    job, comp = parse_simplify_item(item)
    assert job is None

def test_parse_hn_comment_with_links():
    comment = """
    Vercel | San Francisco / Remote | Software Engineer | REMOTE
    We are hiring for our infrastructure team.
    Apply here: https://job-boards.greenhouse.io/vercel/jobs/6105394004
    We build Next.js and global edge infra.
    """
    jobs = parse_hn_comment(comment)
    assert len(jobs) == 1
    assert jobs[0].company == "Vercel"
    assert "https://job-boards.greenhouse.io/vercel/jobs/6105394004" in jobs[0].apply_url
    assert jobs[0].ats == "Greenhouse"

def test_parse_hn_comment_without_links():
    comment = "Just commenting on hiring trends in 2026."
    jobs = parse_hn_comment(comment)
    assert len(jobs) == 0

def test_parse_remotive_item():
    from engine.sources.remotive_feed import parse_remotive_item
    item = {
        "id": 2091177,
        "url": "https://remotive.com/remote-jobs/software-dev/backend-engineer-intern-2091177",
        "title": "Backend Systems Intern",
        "company_name": "Distributed Labs",
        "candidate_required_location": "Worldwide",
        "salary": "$4,000 / month",
        "description": "<p>Go and Kubernetes distributed backend systems</p>",
        "publication_date": "2026-11-20T12:00:00"
    }
    job = parse_remotive_item(item)
    assert job is not None
    assert job.company == "Distributed Labs"
    assert job.title == "Backend Systems Intern"
    assert job.is_internship is True
    assert job.ats == "Remotive"
    assert "Worldwide" in job.location
    assert job.apply_url == "https://remotive.com/remote-jobs/software-dev/backend-engineer-intern-2091177"

def test_parse_himalayas_item():
    from engine.sources.himalayas_feed import parse_himalayas_item
    item = {
        "title": "Software Engineer Intern",
        "companyName": "Hyperscale AI",
        "companySlug": "hyperscale-ai",
        "locationRestrictions": ["Worldwide"],
        "employmentType": "Internship",
        "description": "<p>Python and Go cloud infrastructure</p>",
        "pubDate": 1732000000,
        "applicationLink": "https://jobs.ashbyhq.com/hyperscale/intern"
    }
    job = parse_himalayas_item(item)
    assert job is not None
    assert job.company == "Hyperscale AI"
    assert job.title == "Software Engineer Intern"
    assert job.is_internship is True
    assert job.ats in ["Ashby", "Himalayas"]
    assert "Worldwide" in job.location
    assert job.apply_url == "https://jobs.ashbyhq.com/hyperscale/intern"

def test_simplify_only_discovers_slug_if_geo_valid():
    from engine.sources.simplify_feed import parse_simplify_item

    # US-only listing (e.g. Chevron or Arkansas) should NOT discover slug
    item_us = {
        "active": True,
        "company_name": "US Bank",
        "title": "Software Engineer Intern",
        "url": "https://jobs.ashbyhq.com/usbank/123",
        "locations": ["Dallas, TX (US Only)"]
    }
    job_us, comp_us = parse_simplify_item(item_us)
    assert job_us is not None
    assert comp_us is None, "Expected US-only listing NOT to discover company slug"

    # Worldwide remote listing SHOULD discover slug
    item_remote = {
        "active": True,
        "company_name": "GlobalDev",
        "title": "Software Engineer Intern",
        "url": "https://jobs.ashbyhq.com/globaldev/456",
        "locations": ["Worldwide Remote"]
    }
    job_rem, comp_rem = parse_simplify_item(item_remote)
    assert job_rem is not None
    assert comp_rem is not None
    assert comp_rem["slug"] == "globaldev"

def test_himalayas_search_salary_keys_and_remote_tagging():
    from engine.sources.himalayas_feed import parse_himalayas_item
    # Test with minSalary, maxSalary, salaryPeriod and locationRestrictions: ["India"]
    item = {
        "title": "Backend Engineering Intern",
        "companyName": "RemoteCo",
        "locationRestrictions": ["India"],
        "employmentType": "Internship",
        "description": "<p>Go and Python microservices</p>",
        "minSalary": 30000,
        "maxSalary": 40000,
        "salaryPeriod": "monthly",
        "currency": "INR",
        "applicationLink": "https://jobs.ashbyhq.com/remoteco/intern"
    }
    job = parse_himalayas_item(item)
    assert job is not None
    assert job.location == "India (Remote)"
    assert "30,000" in job.compensation_str or "30k" in job.compensation_str.lower()
    
    # Test IN mapping to India (Remote)
    item_in = {
        "title": "Systems Intern",
        "companyName": "TechStart",
        "locationRestrictions": ["IN"],
        "employmentType": "Intern",
        "applicationLink": "https://techstart.io/apply"
    }
    job_in = parse_himalayas_item(item_in)
    assert job_in is not None
    assert job_in.location == "India (Remote)"

def test_remotive_location_remote_tagging():
    from engine.sources.remotive_feed import parse_remotive_item
    item_india = {
        "id": 101,
        "url": "https://remotive.com/job/101",
        "title": "Cloud Systems Intern",
        "company_name": "CloudCo",
        "candidate_required_location": "India",
        "description": "Docker and Kubernetes",
        "publication_date": "2026-11-20"
    }
    job_india = parse_remotive_item(item_india)
    assert job_india is not None
    assert job_india.location == "India (Remote)"

    item_apac = {
        "id": 102,
        "url": "https://remotive.com/job/102",
        "title": "DevOps Engineer Intern",
        "company_name": "CloudCo",
        "candidate_required_location": "APAC",
        "description": "AWS and Terraform",
        "publication_date": "2026-11-20"
    }
    job_apac = parse_remotive_item(item_apac)
    assert job_apac is not None
    assert job_apac.location == "APAC (Remote)"


