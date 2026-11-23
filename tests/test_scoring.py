import pytest
from engine.analyzer.tech_scorer import score_job_requisition

def test_tier_1_scoring_for_flagship_stack():
    title = "Systems Infrastructure Engineer"
    text = "We are seeking an engineer to build container runtimes using Go, Docker, gVisor, Kubernetes, and AWS with high throughput."
    score, is_tier_1, breakdown, rationale = score_job_requisition(
        title=title,
        job_text=text,
        company="Modal",
        location_type="Worldwide Remote",
        is_internship=False,
        pay_tier_val="Full-Time: 45 – 60 LPA",
        geo_boost=20
    )
    assert score >= 75
    assert is_tier_1
    assert "Go" in rationale or "Docker" in rationale
    assert breakdown["stack_points"] >= 28

def test_soft_penalty_for_cgpa_cutoff():
    title = "Backend Engineer"
    text = "Building Python and FastAPI microservices. Note: Requires minimum 8.0 CGPA or 80% aggregate."
    score, is_tier_1, breakdown, rationale = score_job_requisition(
        title=title,
        job_text=text,
        company="Startup",
        location_type="India (Remote)",
        is_internship=False,
        pay_tier_val="Full-Time: 15 – 30 LPA",
        geo_boost=18
    )
    assert breakdown["penalties"] >= 5
    assert any("CGPA" in note for note in breakdown["penalty_notes"])

def test_founder_email_boosts_prestige():
    title = "Systems Engineer"
    text = "Building distributed engines in Go."
    score, is_tier_1, breakdown, rationale = score_job_requisition(
        title=title,
        job_text=text,
        company="Acme AI",
        location_type="Worldwide Remote",
        is_internship=False,
        pay_tier_val="[Unlisted Salary]",
        geo_boost=20,
        contact_email="founder@acme.ai"
    )
    assert breakdown["prestige_points"] >= 5

def test_intern_title_25_points_regex():
    intern_titles = [
        "Software Engineer Intern",
        "Software Engineering Intern",
        "Software Development Intern",
        "AI Engineer Intern",
        "Cloud Intern",
        "Backend Intern",
        "Backend Engineer Intern",
        "Systems Intern",
        "Systems Engineer Intern",
        "Frontend Intern",
        "Full Stack Intern",
        "ML Engineer Intern",
        "DevOps Intern",
        "Engineering Intern"
    ]
    for t in intern_titles:
        score, is_t1, breakdown, _ = score_job_requisition(
            title=t,
            job_text="",
            company="Startup",
            location_type="Worldwide Remote",
            is_internship=True,
            pay_tier_val="[Unlisted Stipend]",
            geo_boost=20
        )
        assert breakdown["role_points"] == 25, f"Failed for title: {t}, got {breakdown['role_points']}"

def test_go_vs_go_to_market_false_positives():
    # False positive test: go-to-market should NOT trigger Go / Golang points
    text_gtm = "We need an engineer to support our go-to-market and Go-To-Market team to help us go live and go forward."
    score, _, breakdown, rationale = score_job_requisition(
        title="Solutions Developer",
        job_text=text_gtm,
        company="Enterprise",
        location_type="Worldwide Remote",
        is_internship=False,
        pay_tier_val="[Unlisted Salary]"
    )
    assert "Go / Golang" not in breakdown["matched_skills"], f"Go falsely matched: {breakdown['matched_skills']}"

    # True positive test: Go programming should trigger Go / Golang points
    text_go = "Building low-latency services in Go, Kubernetes, and Python."
    score_go, _, breakdown_go, _ = score_job_requisition(
        title="Software Engineer",
        job_text=text_go,
        company="Enterprise",
        location_type="Worldwide Remote",
        is_internship=False,
        pay_tier_val="[Unlisted Salary]"
    )
    assert "Go / Golang" in breakdown_go["matched_skills"]

def test_go_sentence_starter_false_positives():
    # Sentence-starting English "Go build" or "Go create" should NOT trigger Go/Golang points
    english_sentences = [
        "Go build the future with our team.",
        "Go create exceptional experiences for our users.",
        "Go innovate in cloud solutions.",
        "At our startup, you can go explore new ideas."
    ]
    for s in english_sentences:
        _, _, breakdown, _ = score_job_requisition(
            title="Software Engineer",
            job_text=s,
            company="Startup",
            location_type="Worldwide Remote",
            is_internship=False,
            pay_tier_val="[Unlisted Salary]"
        )
        assert "Go / Golang" not in breakdown["matched_skills"], f"Go falsely matched in sentence: '{s}'"

    # Genuine technical list/context forms MUST match
    valid_tech_contexts = [
        "Required skills: Go, Docker, Kubernetes",
        "Experience in Go and Python",
        "Proficient with Go and AWS",
        "Systems written using Go",
        "Knowledge of Go (Golang)",
        "Backend stack: Python/Go/C++",
        "Go/Python microservices",
        "Strong Golang fundamentals"
    ]
    for vt in valid_tech_contexts:
        _, _, breakdown, _ = score_job_requisition(
            title="Software Engineer",
            job_text=vt,
            company="Startup",
            location_type="Worldwide Remote",
            is_internship=False,
            pay_tier_val="[Unlisted Salary]"
        )
        assert "Go / Golang" in breakdown["matched_skills"], f"Go failed to match in valid context: '{vt}'"

