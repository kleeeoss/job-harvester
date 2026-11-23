# Job Harvester V3 Engine — Internet-Scale Harvest & Strict Tiering

An automated, high-throughput, invariant-enforcing job and internship harvester tailored specifically for **Garv Vaidya** (B.Tech CSE, Class of 2027, Hitkarini College of Engineering and Technology Jabalpur, CGPA 7.17).

Built with **Zero Overhead / $0.00 Cost**: Concurrently queries public JSON APIs of 11 major Applicant Tracking Systems alongside 4 live public remote & startup feeds, with SQLite WAL stateful persistence, deep full-text requirement analysis, 0–100 technical stack alignment scoring, and live link verification.

---

## Enforced Invariants (`RULE[user_global]`)

1. **Strictly Direct Requisition Endpoints**:
   - Zero generic career homepages (e.g. `company.com/careers` or `amazon.jobs`). Every listed position points directly to an active ATS requisition (`jobs.ashbyhq.com/...`, `job-boards.greenhouse.io/...`, `jobs.lever.co/...`) or a verified founder contact (`mailto:`).
2. **Mandatory Live Verification Gate**:
   - Every external requisition is verified live before report generation. Direct public ATS JSON API responses are trusted by schema, while external links confirm HTTP 200 and reject expired postings.
3. **Anti-Monopoly Guardrail (`DEFAULT_MAX_ROLES_PER_COMPANY = 3`)**:
   - Caps any single company to at most 3 verified positions in the report, sorted descending by technical stack alignment score.
   - Prevents single-company monopolization, ensuring broad representation across dozens of tech leaders. Configurable via `--no-cap`.
4. **Strict Separation of Internships vs Jobs by Exact Pay Tiers**:
   - **Part 1: Internships** (strictly 100% remote only — India Remote or Worldwide Remote):
     - `Internships: ₹10,000 – ₹20,000 / month`
     - `Internships: ₹20,000 – ₹30,000 / month`
     - `Internships: ₹30,000 – ₹40,000 / month`
     - `Internships: ₹40,000 – ₹50,000 / month` (capped at ₹50k/mo)
     - `[Unlisted Stipend: Venture-Backed Competitive]`
   - **Part 2: Full-Time Engineering Jobs** (Remote / On-site explicitly annotated in location column):
     - `Full-Time: 10 – 15 LPA`
     - `Full-Time: 15 – 30 LPA`
     - `Full-Time: 30 – 45 LPA`
     - `Full-Time: 45 – 60 LPA` (and 45+ LPA / Global USD)
     - `[Unlisted Salary: Venture-Backed Competitive]`
5. **Strict Seniority & Eligibility Filtering**:
   - **Seniority Gating**: Hard exclusion of Senior, Staff, Principal, Lead, SDE2, Architect, Manager, Director, VP, and 3+ YOE management roles.
   - **Title Exclusions**: Excludes non-engineering functions (DevRel, Technical Writer, Sales Engineer, SDET / QA Automation).
   - **Freshness Window**: 120-day cutoff for direct public ATS API boards, 90-day cutoff for internships, and 30-day cutoff for dynamic web feeds.
6. **Technical Stack Scoring (0–100 Scale)**:
   - Evaluates direct alignment with Go, Python, FastAPI, Docker / gVisor, Kubernetes, AWS, Terraform / IaC, Distributed Systems, CI/CD, DevSecOps, and Vertex AI / LLMs.
   - Thresholds: $\ge 35$ for internships, $\ge 55$ for full-time roles; $\ge 75$ flagged as `⭐ Tier 1 Target`.
7. **Negative Finding Integrity**:
   - If an employer in the target roster has zero live off-campus engineering openings matching criteria, it is explicitly declared `0 MATCHING ROLES`. Listings are never hypothesized.

---

## Architecture & Ingestion Streams

### 11 Public ATS Resolvers
- **Ashby** (`engine/resolvers/ashby.py`): Public job board JSON API with compensation extraction
- **Greenhouse** (`engine/resolvers/greenhouse.py`): Job boards API with department & location parsing
- **Lever** (`engine/resolvers/lever.py`): Public postings API with epoch timestamp handling
- **Workday** (`engine/resolvers/workday.py`): CXS API with `postingAvailable: true` verification
- **EU Lever** (`engine/resolvers/eu_lever.py`): European Lever instances
- **Gem** (`engine/resolvers/gem.py`): Gem ATS board endpoints
- **Personio** (`engine/resolvers/personio.py`): Personio XML/JSON job feed parsing
- **Recruitee** (`engine/resolvers/recruitee.py`): Recruitee public careers API
- **Rippling** (`engine/resolvers/rippling.py`): Rippling public board endpoints
- **SmartRecruiters** (`engine/resolvers/smartrecruiters.py`): SmartRecruiters postings API
- **Workable** (`engine/resolvers/workable.py`): Workable public widget & jobs API

### 4 Live Public Dynamic Streams
- **Himalayas** (`engine/sources/himalayas_feed.py`): Filtered Search API querying remote internships & entry-level roles with salary parsing
- **Remotive** (`engine/sources/remotive_feed.py`): Remote engineering & internship API with automatic remote tagging
- **SimplifyJobs** (`engine/sources/simplify_feed.py`): Open internship & new-grad data streams with geo-gated ATS slug auto-discovery
- **Hacker News "Who is hiring?"** (`engine/sources/hn_feed.py`): Live monthly threads with founder email extraction (`DIRECT_FOUNDER_EMAIL`) and job-seeker post rejection

### SQLite WAL Statefulness (`engine/database.py`)
- High-concurrency state store configured with `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
- Tracks scraped requisitions (`jobs` table with composite key `SHA256(company_slug + title + canonical_url)`).
- Auto-persists newly discovered company slugs (`companies` table with `UNIQUE(slug, ats_type)`).

---

## Project Structure

```
Job Harvester/
├── config/
│   ├── settings.py           # Core stack definitions, pay tiers, freshness windows, concurrency limits
│   └── companies.json        # Curated catalog of 300+ Indian tech firms & global remote leaders
├── engine/
│   ├── database.py           # SQLite WAL persistence layer & company discovery
│   ├── models.py             # Data models (JobRequisition, HarvestResult, PayTier)
│   ├── harvester.py          # Asynchronous orchestration engine (Semaphore=20)
│   ├── sources/              # Dynamic ingestion streams
│   │   ├── himalayas_feed.py # Himalayas Search API resolver
│   │   ├── hn_feed.py        # Hacker News monthly thread scraper & email extractor
│   │   ├── remotive_feed.py  # Remotive remote job stream
│   │   └── simplify_feed.py  # SimplifyJobs stream & slug discovery
│   ├── resolvers/            # 11 public ATS JSON API resolvers
│   │   ├── ashby.py, greenhouse.py, lever.py, workday.py, ...
│   ├── analyzer/             # Full-text filters & scoring
│   │   ├── compensation.py   # Exact INR/USD salary & stipend tier categorizer
│   │   ├── eligibility.py    # Seniority exclusions, epoch date parsing, degree safeguards
│   │   ├── geo_filter.py     # Precise location parsing (India remote/on-site vs foreign remote)
│   │   ├── tech_scorer.py    # 0–100 technical stack alignment scoring
│   │   └── text_extractor.py # HTML normalization & cleaning
│   ├── verifier/             # Live HTTP status & endpoint verification
│   │   └── link_verifier.py  # Async HTTP 200 status checker
│   └── output/               # Output report generation
│       └── markdown_gen.py   # Part 1 (Internships), Part 2 (Jobs), and Negative Finding Audit table
├── tests/                    # 112 automated unit tests across 12 test suites (pytest)
├── reports/                  # Generated Markdown reports (harvest_YYYY-MM-DD.md)
├── harvest.py                # Main CLI entrypoint
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quick Start & Usage

### 1. Setup Virtual Environment
```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run Test Suite (TDD Verification)
```bash
pytest -v
```

### 3. Live Harvest Execution (On-Demand)

Run full internet-scale harvest across 300+ companies, live feeds, and discovered slugs:
```bash
python harvest.py --limit 1000 --all --include-discovered
```

Run quick harvest on curated seed list:
```bash
python harvest.py --quick
```

Filter by a specific company slug:
```bash
python harvest.py --company supabase
```
