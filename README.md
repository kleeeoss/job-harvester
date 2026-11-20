# 🎯 Job Harvester Engine

An automated, invariant-enforcing job and internship harvester tailored specifically for **Garv Vaidya** (B.Tech CSE, Class of 2027, Hitkarini College of Engineering and Technology Jabalpur, CGPA 7.17).

Built with **Zero Overhead / $0.00 Cost**: Directly queries public JSON APIs of major Applicant Tracking Systems (**Ashby**, **Greenhouse**, **Lever**, and **Workday**) with deep full-text requirement analysis and mandatory live link verification.

---

## 🛡️ Enforced Invariants (`RULE[user_global]`)

1. **Strictly Direct Requisition Endpoints**:
   - Zero generic career homepages (e.g. `company.com/careers` or `amazon.jobs`). Every listed position points directly to an active application endpoint (`jobs.ashbyhq.com/...`, `boards.greenhouse.io/...`, `jobs.lever.co/...`).
2. **Mandatory Live Verification Gate**:
   - Every single link is fetched live before report generation.
   - Verifies HTTP Status 200, checks Workday `postingAvailable: true`, confirms active Apply buttons/forms, and rejects positions marked "This position has been filled".
3. **Strict Eligibility & Constraint Safeguards**:
   - **Graduation Batch**: Class of 2027 / 3rd-year undergraduate eligible. Rejects 2024/2025-only gated roles.
   - **Academic Cutoffs**: Safeguards candidate's CGPA 7.17 by rejecting roles with mandatory 8.0+ or 80%+ cutoffs.
   - **Location & Work Authorization**:
     - **India Roles**: Both Remote AND On-site are acceptable.
     - **Foreign / International Roles**: Strictly 100% Fully Remote only (discards foreign on-site/hybrid, US-only work authorization, security clearances, or C2C).
4. **Compensation Pay Tiers**:
   - **Internships**: Grouped into ₹10k–₹20k/mo, ₹20k–₹30k/mo, and ₹30k–₹50k/mo (capped at 50k). Discards unpaid or <₹10k/mo.
   - **Full-Time Jobs**: Grouped into 10–15 LPA, 15–30 LPA, and 30–60 LPA (capped at 60 LPA). Discards <10 LPA.
   - **Venture-Backed Unlisted Startups**: Explicitly badged as `[Unlisted Salary: Venture-Backed Competitive]`.
   - **Top-Tier / High-Compensation Section**: Prominent separate section for opportunities offering >= 20 LPA, >= ₹30,000/mo stipend, or top-tier tech companies (Modal, Sarvam AI, Perplexity, Supabase, Cursor, Razorpay, etc.).
5. **Negative Finding Integrity**:
   - If an employer in the target roster has zero live off-campus undergraduate openings matching the criteria, it is explicitly declared `CLOSED / ZERO REQUISITIONS`. Listings are never hypothesized.

---

## 📂 Project Structure

```
C:\Users\User\Programs\Job Harvester\
├── config/
│   ├── settings.py           # Candidate profile, constants, pay tier limits, top-tier company roster
│   └── companies.json        # Curated catalog of target companies (Ashby, Greenhouse, Lever, Workday)
├── engine/
│   ├── models.py             # Data models (JobRequisition, HarvestResult, PayTier)
│   ├── harvester.py          # Orchestration pipeline
│   ├── resolvers/            # Public ATS JSON API resolvers
│   │   ├── ashby.py          # Ashby posting API
│   │   ├── greenhouse.py     # Greenhouse boards API
│   │   ├── lever.py          # Lever postings API
│   │   └── workday.py        # Workday postingAvailable gate
│   ├── analyzer/             # Deep full-text constraint analysis
│   │   ├── text_extractor.py # Normalization and HTML stripping
│   │   ├── eligibility.py    # Batch 2027, CGPA 7.17, citizenship/clearance filtering
│   │   ├── location.py       # India (remote/on-site) vs Foreign (100% remote only)
│   │   ├── compensation.py   # Regex extraction for INR/USD salaries & stipends
│   │   └── tech_scorer.py    # Stack match scoring (Go, Python, Docker, K8s, AWS, Systems)
│   ├── verifier/             # Live HTTP & DOM verification gate
│   │   └── link_verifier.py  # Asynchronous HTTP 200 + active application form/button checker
│   └── output/               # Output report and cold pitch generation
│       ├── cold_pitch_gen.py # Tailored 75-word founder pitches referencing garvvaidya.vercel.app
│       └── markdown_gen.py   # Pay tier groupings, Top-tier section, negative finding table
├── tests/                    # 34 automated unit tests (pytest)
├── reports/                  # Generated Markdown action sheets (harvest_YYYY-MM-DD.md)
├── harvest.py                # Main CLI entrypoint
├── requirements.txt
└── README.md
```

---

## ⚡ Quick Start & Usage

### 1. Run Unit Tests (TDD Verification)
```bash
.venv\Scripts\pytest
```

### 2. Manual Harvest Execution (On-Demand)

Run full harvest across all curated companies:
```bash
.venv\Scripts\python harvest.py
```

Run quick harvest on top target companies (Modal, Sarvam AI, Perplexity, Supabase, Cursor, Linear):
```bash
.venv\Scripts\python harvest.py --quick
```

Filter by a specific target company:
```bash
.venv\Scripts\python harvest.py --company sarvam
.venv\Scripts\python harvest.py --company modal
.venv\Scripts\python harvest.py --company razorpay
```

### 3. Review Generated Harvest Report
The Markdown report is generated with live, clickable direct application links in:
```
reports/harvest_YYYY-MM-DD.md
```
