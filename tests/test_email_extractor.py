import pytest
from engine.sources.hn_feed import extract_founder_emails, parse_hn_comment

def test_extract_direct_founder_emails():
    text = "We are hiring! Reach out directly to founder@startup.ai or engineering@deeptech.io."
    emails = extract_founder_emails(text)
    assert "founder@startup.ai" in emails
    assert "engineering@deeptech.io" in emails

def test_extract_obfuscated_founder_emails():
    text = "Send your resume to alex [at] hyperscale (dot) ai or jobs at acme dot co dot uk"
    emails = extract_founder_emails(text)
    assert "alex@hyperscale.ai" in emails
    assert "jobs@acme.co.uk" in emails

def test_reject_domain_words_false_positives():
    text = "We run platform.io for data processing and please run format.py before sending."
    emails = extract_founder_emails(text)
    assert len(emails) == 0

def test_hn_comment_generates_direct_founder_email_job():
    comment_html = """
    Acme Systems | Backend Engineer | Remote (Worldwide) | Full-time
    We are building a distributed cache in Go.
    Email founder [at] acmesystems dot ai directly to chat!
    """
    jobs = parse_hn_comment(comment_html, comment_id="12345")
    assert len(jobs) >= 1
    job = jobs[0]
    assert job.ats == "DIRECT_FOUNDER_EMAIL"
    assert job.contact_email == "founder@acmesystems.ai"
    assert job.apply_url == "mailto:founder@acmesystems.ai"
    assert "Acme Systems" in job.company
    assert "Backend Engineer" in job.title

def test_hn_comment_html_p_br_header_parsing():
    comment_html = "<p>CloudScale | Infrastructure Engineer | Remote | Full-time</p><p>We build Kubernetes operators.<br>Contact us at jobs@cloudscale.io</p>"
    jobs = parse_hn_comment(comment_html, comment_id="99999")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.company == "CloudScale"
    assert job.title == "Infrastructure Engineer"
    assert "Remote" in job.location
    assert job.contact_email == "jobs@cloudscale.io"
    assert job.hn_permalink == "https://news.ycombinator.com/item?id=99999"

def test_ignore_personal_webmail_without_company_header():
    # Personal webmail without pipe header should be rejected
    comment_no_header = "<p>Looking for someone to help with my app, email me at johnny123@gmail.com</p>"
    jobs_no_header = parse_hn_comment(comment_no_header, comment_id="88888")
    assert len(jobs_no_header) == 0

    # Personal webmail with genuine company header should be accepted
    comment_with_header = "<p>StealthRobotics | Systems Intern | Remote</p><p>Email roboticsfounder@gmail.com</p>"
    jobs_with_header = parse_hn_comment(comment_with_header, comment_id="77777")
    assert len(jobs_with_header) == 1
    assert jobs_with_header[0].company == "StealthRobotics"

def test_hn_comment_rejects_no_pipe_header_and_random_commenters():
    from engine.sources.hn_feed import parse_hn_comment

    # Random dev comment with personal domain and no pipe header or hiring keywords
    comment = "<p>Interesting project! Check out my blog or reach me at wm@wagnermatos.co.uk</p>"
    jobs = parse_hn_comment(comment, comment_id="99991")
    assert len(jobs) == 0, "Expected comment without hiring context or pipe header to be rejected"

    # Comment from an IT consulting domain without hiring intent
    comment2 = "<p>We had a similar outage last week. Ping cprabala@techmahindra.com</p>"
    jobs2 = parse_hn_comment(comment2, comment_id="99992")
    assert len(jobs2) == 0

def test_hn_comment_rejects_job_seekers():
    from engine.sources.hn_feed import parse_hn_comment

    # Job seeker posting their resume / availability
    comment = "<p>Seeking a role | Backend Engineer | Remote</p><p>I am available immediately for hire. My resume is at example.com/resume. Contact dev@candidate.ai</p>"
    jobs = parse_hn_comment(comment, comment_id="99993")
    assert len(jobs) == 0, "Expected job-seeker comment to be rejected"

    comment2 = "<p>Looking for a position in distributed systems. Available for freelance or full-time. Contact: eng@coder.io</p>"
    jobs2 = parse_hn_comment(comment2, comment_id="99994")
    assert len(jobs2) == 0, "Expected job-seeker comment to be rejected"

