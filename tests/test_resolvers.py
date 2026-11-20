import pytest
from engine.resolvers.ashby import parse_ashby_payload
from engine.resolvers.greenhouse import parse_greenhouse_payload
from engine.resolvers.lever import parse_lever_payload
from engine.resolvers.workday import parse_workday_payload

def test_ashby_resolver_parses_direct_requisitions():
    mock_payload = {
        "jobs": [
            {
                "id": "job_123",
                "title": "Systems Engineer",
                "location": "Remote",
                "isRemote": True,
                "applyUrl": "https://jobs.ashbyhq.com/modal/job_123/application",
                "jobUrl": "https://jobs.ashbyhq.com/modal/job_123",
                "descriptionHtml": "<p>Build high performance Go runtimes.</p>"
            }
        ]
    }
    jobs = parse_ashby_payload("modal", mock_payload)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.company == "modal"
    assert job.title == "Systems Engineer"
    assert job.ats == "Ashby"
    assert "modal/job_123" in job.apply_url
    assert not job.apply_url.endswith("/careers")

def test_greenhouse_resolver_parses_direct_requisitions():
    mock_payload = {
        "jobs": [
            {
                "id": 987654,
                "title": "Backend Engineering Intern",
                "location": {"name": "Bengaluru, India"},
                "absolute_url": "https://boards.greenhouse.io/sarvam/jobs/987654",
                "content": "&lt;p&gt;Work on LLM inference pipelines with Python.&lt;/p&gt;"
            }
        ]
    }
    jobs = parse_greenhouse_payload("sarvam", mock_payload)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.company == "sarvam"
    assert job.title == "Backend Engineering Intern"
    assert job.ats == "Greenhouse"
    assert job.apply_url == "https://boards.greenhouse.io/sarvam/jobs/987654"

def test_lever_resolver_parses_direct_requisitions():
    mock_payload = [
        {
            "id": "lever_456",
            "text": "Infrastructure Engineer",
            "hostedUrl": "https://jobs.lever.co/postman/lever_456",
            "applyUrl": "https://jobs.lever.co/postman/lever_456/apply",
            "categories": {"location": "Remote, India"},
            "description": "<p>Kubernetes and AWS automation.</p>"
        }
    ]
    jobs = parse_lever_payload("postman", mock_payload)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.company == "postman"
    assert job.title == "Infrastructure Engineer"
    assert job.ats == "Lever"
    assert "postman/lever_456" in job.apply_url

def test_workday_resolver_respects_posting_available_invariant():
    # When postingAvailable is True
    open_payload = {
        "jobPostingInfo": {
            "title": "Cloud Platform Engineer",
            "location": "Bangalore, India",
            "postingAvailable": True,
            "externalUrl": "https://myworkdayjobs.com/company/job/123",
            "jobDescription": "Build AWS infrastructure."
        }
    }
    jobs = parse_workday_payload("workday_co", open_payload)
    assert len(jobs) == 1

    # When postingAvailable is False (must be dropped immediately per RULE[user_global])
    closed_payload = {
        "jobPostingInfo": {
            "title": "Cloud Platform Engineer",
            "location": "Bangalore, India",
            "postingAvailable": False,
            "externalUrl": "https://myworkdayjobs.com/company/job/123",
            "jobDescription": "Build AWS infrastructure."
        }
    }
    closed_jobs = parse_workday_payload("workday_co", closed_payload)
    assert len(closed_jobs) == 0
