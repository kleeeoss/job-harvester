import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from .models import JobRequisition, PayTier

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "harvester.db"
)

def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """
    Returns an SQLite connection with WAL mode and busy timeout enabled
    to eliminate database lock issues during concurrent scraping.
    """
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initializes tables and indexes in SQLite."""
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            ats_type TEXT NOT NULL,
            board_url TEXT,
            is_top_tier BOOLEAN DEFAULT 0,
            domain TEXT DEFAULT '',
            discovered_from TEXT DEFAULT 'seed',
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_scanned_at TIMESTAMP,
            UNIQUE(slug, ats_type)
        );
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            company_slug TEXT NOT NULL,
            company_name TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            location_type TEXT NOT NULL,
            apply_url TEXT NOT NULL,
            description_text TEXT,
            is_internship BOOLEAN DEFAULT 0,
            pay_tier TEXT NOT NULL,
            compensation_str TEXT DEFAULT '[Unlisted Salary: Venture-Backed Competitive]',
            ats_type TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            is_tier_1 BOOLEAN DEFAULT 0,
            score_breakdown TEXT,
            status TEXT DEFAULT 'new',
            contact_email TEXT,
            posted_date TEXT,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reported_at TIMESTAMP
        );
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_slug);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_slug_ats ON companies(slug, ats_type);")
    conn.close()

def generate_job_id(company_slug: str, title: str, apply_url: str, comment_id: Optional[str] = None, email: Optional[str] = None) -> str:
    """Generates a deterministic 16-character SHA-256 identifier."""
    if comment_id and email:
        raw = f"hn:{comment_id}:{email.lower().strip()}:{title.lower().strip()}"
    else:
        raw = f"{company_slug.lower().strip()}:{title.lower().strip()}:{apply_url.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

def upsert_companies(companies: List[Dict[str, Any]], db_path: str = DEFAULT_DB_PATH) -> int:
    """Batch upserts companies into the SQLite companies catalog."""
    if not companies:
        return 0
    conn = get_db_connection(db_path)
    inserted = 0
    with conn:
        for c in companies:
            slug = c.get("slug", "").strip().lower()
            ats = c.get("ats", c.get("ats_type", "ashby")).strip().lower()
            name = c.get("name", slug)
            if not slug or not ats:
                continue
            discovered = c.get("discovered_from", "seed")
            if discovered == "seed":
                cur = conn.execute("""
                INSERT INTO companies (name, slug, ats_type, board_url, is_top_tier, domain, discovered_from, last_scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(slug, ats_type) DO UPDATE SET
                    name = excluded.name,
                    is_top_tier = MAX(companies.is_top_tier, excluded.is_top_tier),
                    last_scanned_at = CURRENT_TIMESTAMP
                """, (
                    name,
                    slug,
                    ats,
                    c.get("board_url", ""),
                    1 if c.get("is_top_tier") else 0,
                    c.get("domain", ""),
                    discovered
                ))
            else:
                cur = conn.execute("""
                INSERT INTO companies (name, slug, ats_type, board_url, is_top_tier, domain, discovered_from, last_scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(slug, ats_type) DO UPDATE SET
                    name = excluded.name,
                    is_top_tier = MAX(companies.is_top_tier, excluded.is_top_tier)
                """, (
                    name,
                    slug,
                    ats,
                    c.get("board_url", ""),
                    1 if c.get("is_top_tier") else 0,
                    c.get("domain", ""),
                    discovered
                ))
            if cur.rowcount > 0:
                inserted += 1
    conn.close()
    return inserted

def upsert_jobs(jobs: List[JobRequisition], db_path: str = DEFAULT_DB_PATH) -> Dict[str, int]:
    """
    Batch upserts candidate jobs into SQLite.
    Returns: {'net_new': count, 'updated': count}
    """
    if not jobs:
        return {"net_new": 0, "updated": 0}
    conn = get_db_connection(db_path)
    net_new = 0
    updated = 0
    with conn:
        for j in jobs:
            existing = conn.execute("SELECT id, status, reported_at FROM jobs WHERE id = ?", (j.id,)).fetchone()
            if existing is None:
                conn.execute("""
                INSERT INTO jobs (
                    id, company_slug, company_name, title, location, location_type,
                    apply_url, description_text, is_internship, pay_tier, compensation_str,
                    ats_type, score, is_tier_1, score_breakdown, status, contact_email, posted_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    j.id,
                    j.company.lower().strip(),
                    j.company,
                    j.title,
                    j.location,
                    j.location_type,
                    j.apply_url,
                    j.description_text[:4000] if j.description_text else "",
                    1 if j.is_internship else 0,
                    j.pay_tier.value if hasattr(j.pay_tier, "value") else str(j.pay_tier),
                    j.compensation_str,
                    j.ats,
                    j.score,
                    1 if j.is_tier_1 else 0,
                    json.dumps(j.score_breakdown) if hasattr(j, "score_breakdown") and j.score_breakdown else "{}",
                    "new",
                    j.contact_email if hasattr(j, "contact_email") else None,
                    j.posted_date if hasattr(j, "posted_date") else None
                ))
                net_new += 1
            else:
                conn.execute("""
                UPDATE jobs SET
                    last_seen_at = CURRENT_TIMESTAMP,
                    score = ?,
                    is_tier_1 = ?,
                    compensation_str = ?,
                    location = ?
                WHERE id = ?
                """, (
                    j.score,
                    1 if j.is_tier_1 else 0,
                    j.compensation_str,
                    j.location,
                    j.id
                ))
                updated += 1
    conn.close()
    return {"net_new": net_new, "updated": updated}

def get_net_new_jobs(min_score: int = 55, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetches jobs that have not yet been included in a generated report."""
    conn = get_db_connection(db_path)
    rows = conn.execute("""
    SELECT * FROM jobs
    WHERE reported_at IS NULL AND score >= ? AND status = 'new'
    ORDER BY score DESC
    """, (min_score,)).fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def mark_jobs_reported(job_ids: List[str], db_path: str = DEFAULT_DB_PATH) -> None:
    """Marks jobs as reported so subsequent runs output only net-new positions."""
    if not job_ids:
        return
    conn = get_db_connection(db_path)
    with conn:
        conn.executemany("UPDATE jobs SET reported_at = CURRENT_TIMESTAMP WHERE id = ?", [(jid,) for jid in job_ids])
    conn.close()

def get_all_jobs(status: Optional[str] = None, min_score: int = 55, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves stored jobs with optional status filter."""
    conn = get_db_connection(db_path)
    if status:
        rows = conn.execute("SELECT * FROM jobs WHERE status = ? AND score >= ? ORDER BY score DESC", (status, min_score)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs WHERE score >= ? ORDER BY score DESC", (min_score,)).fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results

def get_unreported_job_ids(job_ids: List[str], db_path: str = DEFAULT_DB_PATH) -> Set[str]:
    """Returns the set of job IDs among the provided list where reported_at IS NULL."""
    if not job_ids:
        return set()
    conn = get_db_connection(db_path)
    placeholders = ",".join("?" for _ in job_ids)
    rows = conn.execute(
        f"SELECT id FROM jobs WHERE id IN ({placeholders}) AND reported_at IS NULL",
        job_ids
    ).fetchall()
    unreported = set(r["id"] for r in rows)
    conn.close()
    return unreported

def get_discovered_companies(limit: int = 100, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Returns newly discovered companies from the catalog that haven't been scanned recently."""
    conn = get_db_connection(db_path)
    rows = conn.execute("""
    SELECT name, slug, ats_type as ats, board_url, is_top_tier, domain
    FROM companies
    WHERE discovered_from != 'seed'
    ORDER BY last_scanned_at ASC NULLS FIRST, first_seen_at DESC
    LIMIT ?
    """, (limit,)).fetchall()
    res = [dict(r) for r in rows]
    conn.close()
    return res
