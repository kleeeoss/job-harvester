from typing import List, Dict
from ..models import HarvestResult, JobRequisition, PayTier
from .cold_pitch_gen import generate_cold_pitch
from config.settings import PROFILE

def generate_harvest_report(result: HarvestResult) -> str:
    """
    Renders an executive, actionable Markdown harvest report grouped strictly by:
    1. Top-Tier & High-Compensation Section (>= 20 LPA, >= 30k/mo stipend, or top-tier companies)
    2. Pay Tier Subsections (Internships: 10k-20k, 20k-30k, 30k-50k; Jobs: 10-15 LPA, 15-30 LPA, 30-60 LPA; Unlisted)
    3. Tailored 75-word Cold Outreach Pitch Templates
    4. Negative Finding Integrity Section (explicit closed / zero active listings table)
    """
    lines = []
    lines.append(f"# 🎯 Job & Internship Harvest Report — {result.date_str}")
    lines.append("")
    lines.append(f"**Target Candidate:** [{PROFILE.name}]({PROFILE.portfolio_url}) • B.Tech CSE (Class of 2027) • CGPA {PROFILE.cgpa} • Jabalpur, India")
    lines.append(f"**Core Profile:** Systems Programming, Cloud Infrastructure, Backend (Go, Python, Docker, Kubernetes, AWS, Distributed Systems)")
    lines.append("")
    lines.append("> [!NOTE] **Filters & Invariants Enforced in Code:**")
    lines.append("> • **Location:** India (Remote & On-site Permitted) • Foreign Roles (Strictly 100% Fully Remote Only)")
    lines.append("> • **Graduation Batch:** Class of 2027 / Penultimate Undergraduate Eligible (No 2024/2025-only gating)")
    lines.append("> • **Academic Safety:** CGPA Cutoff <= 7.17 (Zero 8.0+ / 80%+ mandatory cutoffs)")
    lines.append("> • **Verification:** 100% Direct Requisition Endpoints • HTTP 200 & Active Form Confirmed • Zero Career Homepages")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Top-Tier & High-Compensation Section
    top_tier_jobs = [j for j in result.active_jobs if j.is_top_tier]
    lines.append("## 🌟 Section 1: Top-Tier & High-Compensation Opportunities")
    lines.append("*(Roles offering >= 20 LPA, >= ₹30,000/mo stipends, or premier high-paying engineering organizations)*")
    lines.append("")

    if top_tier_jobs:
        lines.append("| Company | Role | Type | Location | Comp / Stipend | Direct Application Link | Stack Match |")
        lines.append("|---|---|---|---|---|---|---|")
        for j in top_tier_jobs:
            role_type = "Internship" if j.is_internship else "Full-Time"
            ats_label = f"Apply on {j.ats}" if j.ats else "Apply Directly"
            link_md = f"[{ats_label}]({j.apply_url})"
            lines.append(f"| **{j.company}** | {j.title} | {role_type} | {j.location} | `{j.compensation_str}` | {link_md} | {j.match_rationale} |")
    else:
        lines.append("*No top-tier roles detected in the current run meeting all strict invariants.*")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Grouped by Pay Tiers
    lines.append("## 💼 Section 2: Requisitions Grouped by Pay Tier")
    lines.append("")

    # Group jobs by tier
    tier_groups: Dict[PayTier, List[JobRequisition]] = {t: [] for t in PayTier}
    for j in result.active_jobs:
        tier_groups[j.pay_tier].append(j)

    tier_order = [
        ("### 🥇 Internships: ₹30,000 – ₹50,000 / month", PayTier.INTERN_30K_50K),
        ("### 🥈 Internships: ₹20,000 – ₹30,000 / month", PayTier.INTERN_20K_30K),
        ("### 🥉 Internships: ₹10,000 – ₹20,000 / month", PayTier.INTERN_10K_20K),
        ("### 🥇 Full-Time: 30 – 60 LPA", PayTier.JOB_30_60_LPA),
        ("### 🥈 Full-Time: 15 – 30 LPA", PayTier.JOB_15_30_LPA),
        ("### 🥉 Full-Time: 10 – 15 LPA", PayTier.JOB_10_15_LPA),
        ("### 🚀 Venture-Backed High Growth Startups [Unlisted Salary: Venture-Backed Competitive]", PayTier.UNLISTED),
    ]

    for header, tier_key in tier_order:
        tier_jobs = tier_groups[tier_key]
        lines.append(header)
        lines.append("")
        if tier_jobs:
            lines.append("| Company | Role | Location | Compensation | Direct Requisition Link | Stack Match |")
            lines.append("|---|---|---|---|---|---|")
            for j in tier_jobs:
                ats_label = f"Apply on {j.ats}" if j.ats else "Direct Requisition"
                lines.append(f"| **{j.company}** | {j.title} | {j.location} | `{j.compensation_str}` | [{ats_label}]({j.apply_url}) | {j.match_rationale} |")
        else:
            lines.append("*No active requisitions in this pay bracket for this scan.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 3. Tailored Cold Pitch Section
    lines.append("## ✉️ Section 3: Tailored 75-Word Founder Cold Outreach Messages")
    lines.append("*(Pre-written, punchy outreach pitches referencing your live portfolio & systems projects)*")
    lines.append("")

    featured_jobs = result.active_jobs[:3]
    if featured_jobs:
        for j in featured_jobs:
            pitch = generate_cold_pitch(j.company, j.title, [j.match_rationale])
            lines.append(f"### Cold Pitch: {j.company} — {j.title}")
            lines.append("```text")
            lines.append(pitch)
            lines.append("```")
            lines.append("")
    else:
        lines.append("*Cold pitch templates will automatically generate when active targets are detected.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 4. Negative Finding Integrity Section
    lines.append("## 🛡️ Section 4: Negative Finding Integrity (Closed / Zero Active Requisitions)")
    lines.append("*(Per systems engineering invariants: Confirms scanned companies where no live undergraduate off-campus requisitions match candidate criteria. Never hypothesized.)*")
    lines.append("")

    if result.closed_companies:
        lines.append("| Scanned Company | Status | Notes |")
        lines.append("|---|---|---|")
        for comp in result.closed_companies:
            lines.append(f"| **{comp}** | `CLOSED / ZERO REQUISITIONS` | No active requisitions meeting Class of 2027 & stack invariants |")
    else:
        lines.append("*All scanned targets had matching positions.*")

    lines.append("")
    lines.append(f"**Total Requisitions Scanned:** {result.total_scanned} | **Verified Matches:** {len(result.active_jobs)}")
    lines.append("")
    return "\n".join(lines)
