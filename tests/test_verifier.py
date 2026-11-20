import pytest
from engine.verifier.link_verifier import verify_html_content, is_career_homepage

def test_detect_career_homepages():
    assert is_career_homepage("https://company.com/careers")
    assert is_career_homepage("https://company.com/jobs")
    assert is_career_homepage("https://amazon.jobs")
    # Must NOT flag direct requisition endpoints
    assert not is_career_homepage("https://boards.greenhouse.io/sarvam/jobs/12345")
    assert not is_career_homepage("https://jobs.lever.co/postman/abcd-1234")
    assert not is_career_homepage("https://app.ashbyhq.com/modal/job-123")

def test_verify_html_active_requisition():
    active_html = """
    <html>
      <body>
        <h1>Systems Engineer</h1>
        <button id="apply-button">Apply for this job</button>
        <form action="/submit">
          <input type="text" name="name" />
          <input type="file" name="resume" />
        </form>
      </body>
    </html>
    """
    valid, reason = verify_html_content(200, active_html, "https://jobs.lever.co/postman/123")
    assert valid
    assert reason == "Active requisition verified"

def test_reject_filled_position():
    filled_html = """
    <html>
      <body>
        <h1>Senior Backend Engineer</h1>
        <div class="closed-banner">This position has been filled. Thank you for your interest.</div>
      </body>
    </html>
    """
    valid, reason = verify_html_content(200, filled_html, "https://boards.greenhouse.io/sarvam/jobs/123")
    assert not valid
    assert "filled" in reason.lower()

def test_reject_non_200_status():
    valid, reason = verify_html_content(404, "Not Found", "https://app.ashbyhq.com/modal/404")
    assert not valid
    assert "404" in reason or "status" in reason.lower()
