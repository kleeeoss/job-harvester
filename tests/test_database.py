import os
import pytest
from engine.database import (
    init_db,
    get_db_connection,
    upsert_companies,
    upsert_jobs,
    get_net_new_jobs,
    mark_jobs_reported,
    generate_job_id
)
from engine.models import JobRequisition, PayTier

TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_harvester.db")

@pytest.fixture(autouse=True)
def clean_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    init_db(TEST_DB_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

def test_sqlite_wal_mode_enabled():
    conn = get_db_connection(TEST_DB_PATH)
    mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    conn.close()
    assert mode.lower() == "wal"

def test_company_composite_unique_key():
    # Same slug across different ATS boards should NOT collide
    comps = [
        {"name": "Sentry Greenhouse", "slug": "sentry", "ats": "greenhouse"},
        {"name": "Sentry Ashby", "slug": "sentry", "ats": "ashby"},
    ]
    upsert_companies(comps, TEST_DB_PATH)
    conn = get_db_connection(TEST_DB_PATH)
    rows = conn.execute("SELECT slug, ats_type FROM companies").fetchall()
    conn.close()
    assert len(rows) == 2

def test_job_upsert_and_net_new_tracking():
    jid = generate_job_id("modal", "Systems Engineer", "https://jobs.ashbyhq.com/modal/1")
    job = JobRequisition(
        id=jid,
        company="Modal",
        title="Systems Engineer",
        location="Remote",
        apply_url="https://jobs.ashbyhq.com/modal/1",
        description_text="Go systems engineering",
        score=85,
        is_tier_1=True,
        pay_tier=PayTier.JOB_45_60_LPA
    )

    stats = upsert_jobs([job], TEST_DB_PATH)
    assert stats["net_new"] == 1

    # Should be net-new
    net_new = get_net_new_jobs(min_score=55, db_path=TEST_DB_PATH)
    assert len(net_new) == 1
    assert net_new[0]["id"] == jid
    assert net_new[0]["is_tier_1"] == 1

    # Mark as reported
    mark_jobs_reported([jid], TEST_DB_PATH)

    # Next run should show 0 net-new
    assert len(get_net_new_jobs(min_score=55, db_path=TEST_DB_PATH)) == 0

    # Upserting same job updates timestamp rather than inserting duplicate
    stats2 = upsert_jobs([job], TEST_DB_PATH)
    assert stats2["net_new"] == 0
    assert stats2["updated"] == 1

def test_get_unreported_job_ids_and_discovered_companies():
    from engine.database import get_unreported_job_ids, get_discovered_companies

    jid1 = generate_job_id("co1", "Engineer", "https://ashbyhq.com/co1/1")
    jid2 = generate_job_id("co2", "Intern", "https://ashbyhq.com/co2/2")

    job1 = JobRequisition(id=jid1, company="Co1", title="Engineer", location="Remote", apply_url="https://ashbyhq.com/co1/1")
    job2 = JobRequisition(id=jid2, company="Co2", title="Intern", location="Remote", apply_url="https://ashbyhq.com/co2/2", is_internship=True)

    upsert_jobs([job1, job2], TEST_DB_PATH)

    # Both are unreported initially
    unreported = get_unreported_job_ids([jid1, jid2], TEST_DB_PATH)
    assert unreported == {jid1, jid2}

    # Mark job1 reported
    mark_jobs_reported([jid1], TEST_DB_PATH)
    assert get_unreported_job_ids([jid1, jid2], TEST_DB_PATH) == {jid2}

    # Discovered companies query
    comps = [
        {"name": "SeedCo", "slug": "seedco", "ats": "ashby", "discovered_from": "seed"},
        {"name": "DiscCo", "slug": "discco", "ats": "lever", "discovered_from": "simplify_feed"}
    ]
    upsert_companies(comps, TEST_DB_PATH)

    disc = get_discovered_companies(limit=10, db_path=TEST_DB_PATH)
    assert len(disc) == 1
    assert disc[0]["slug"] == "discco"
