import pytest
from engine.resolvers.workable import parse_workable_payload, is_valid_workable_slug
from engine.resolvers.ashby import parse_ashby_payload
from engine.models import PayTier

def test_workable_reserved_slug_filtering():
    assert not is_valid_workable_slug("j")
    assert not is_valid_workable_slug("api")
    assert not is_valid_workable_slug("view")
    assert not is_valid_workable_slug("embed")
    assert is_valid_workable_slug("aerotime")
    assert is_valid_workable_slug("incred-financial")

def test_workable_payload_parsing_and_shortcode_dedup():
    data = {
        "jobs": [
            {
                "id": "1",
                "shortcode": "ABC123",
                "title": "Backend Engineer",
                "city": "Bengaluru",
                "country": "India",
                "telecommuting": True,
                "shortlink": "https://apply.workable.com/test/j/ABC123/",
                "description": "<p>Go and Python microservices</p>"
            },
            {
                # Duplicate shortcode from multi-location listing
                "id": "2",
                "shortcode": "ABC123",
                "title": "Backend Engineer",
                "city": "Delhi",
                "country": "India",
                "telecommuting": True,
                "shortlink": "https://apply.workable.com/test/j/ABC123/",
                "description": "<p>Go and Python microservices</p>"
            }
        ]
    }
    jobs = parse_workable_payload("test", data)
    assert len(jobs) == 1
    assert jobs[0].id == "ABC123"
    assert jobs[0].ats == "Workable"
    assert "Remote" in jobs[0].location

def test_ashby_is_listed_gate_and_structured_compensation():
    data = {
        "jobs": [
            {
                "id": "job_1",
                "title": "Systems Engineer",
                "isListed": True,
                "location": "Remote",
                "compensation": {
                    "scrapeableCompensationSalarySummary": "$180K - $220K"
                }
            },
            {
                "id": "job_2",
                "title": "Internal Confidential Role",
                "isListed": False,
                "location": "Remote"
            }
        ]
    }
    jobs = parse_ashby_payload("modal", data)
    assert len(jobs) == 1
    assert jobs[0].id == "job_1"
    assert jobs[0].compensation_str == "$180K - $220K"
    assert jobs[0].pay_tier in [PayTier.JOB_30_45_LPA, PayTier.JOB_45_60_LPA]

def test_ashby_comma_formatted_salary_range():
    data = {
        "jobs": [
            {
                "id": "job_comma_1",
                "title": "Cloud Infrastructure Engineer",
                "isListed": True,
                "location": "Worldwide Remote",
                "compensation": {
                    "scrapeableCompensationSalarySummary": "$126,000 - $210,000"
                }
            }
        ]
    }
    jobs = parse_ashby_payload("startup", data)
    assert len(jobs) == 1
    assert jobs[0].id == "job_comma_1"
    assert jobs[0].compensation_str == "$126,000 - $210,000"
    assert jobs[0].pay_tier == PayTier.JOB_45_60_LPA


@pytest.mark.anyio
async def test_personio_com_domain_and_operator_precedence():
    import httpx
    from engine.resolvers.personio import fetch_personio_jobs

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <workzag-jobs>
      <position>
        <id>1001</id>
        <name>Backend Engineer</name>
        <office>Berlin</office>
        <employmentType>permanent</employmentType>
        <schedule>full-time</schedule>
        <createdAt>2026-11-20T10:00:00Z</createdAt>
      </position>
    </workzag-jobs>
    """

    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            # Simulate .de 404 returning XML error body, .com 200 returning valid XML
            if ".de" in url_str:
                return httpx.Response(status_code=404, text="<?xml error>", headers={"content-type": "text/xml"})
            elif ".com" in url_str:
                return httpx.Response(status_code=200, text=xml_content, headers={"content-type": "application/xml"})
            return httpx.Response(status_code=404)

    async with httpx.AsyncClient(transport=MockTransport()) as client:
        jobs = await fetch_personio_jobs(client, "deeptech")
        assert len(jobs) == 1
        assert jobs[0].id == "1001"
        assert "personio.com" in jobs[0].apply_url, f"Expected .com in apply_url, got {jobs[0].apply_url}"
