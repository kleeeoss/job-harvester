from typing import List, Dict
from ..models import HarvestResult, JobRequisition, PayTier
from config.settings import PROFILE

def format_location(job: JobRequisition) -> str:
    loc = job.location.strip()
    if not loc:
        return f"`{job.location_type}`"
    if loc.lower() in [job.location_type.lower(), "remote", "worldwide remote", "india remote"]:
        return f"`{job.location_type}`"
    if len(loc) > 75:
        if "india" in loc.lower():
            loc = "Multi-region (incl. India)"
        elif "remote" in loc.lower() and loc.count("/") > 3:
            loc = "Worldwide Remote (Multi-region)"
        else:
            loc = loc[:72] + "..."
    if f"`{job.location_type}`" in loc:
        return loc
    return f"{loc} • `{job.location_type}`"

def format_link_cell(job: JobRequisition) -> str:
    if job.ats == "DIRECT_FOUNDER_EMAIL" or (job.contact_email and job.apply_url.startswith("mailto:")):
        email = job.contact_email or job.apply_url.replace("mailto:", "")
        link = f"[📧 Email Founder ({email})](mailto:{email})"
        if job.hn_permalink:
            link += f" • [HN Post]({job.hn_permalink})"
        return link
    ats_label = f"Apply on {job.ats}" if job.ats else "Direct Requisition"
    return f"[{ats_label}]({job.apply_url})"

def format_score_badge(job: JobRequisition) -> str:
    if job.is_tier_1 or job.score >= 75:
        return f"**{job.score}** `⭐ Tier 1`"
    return f"{job.score}"

def generate_harvest_report(result: HarvestResult) -> str:
    """
    Renders an executive, actionable Markdown harvest report:
    1. Part 1: Internships (10k-20k, 20k-30k, 30k-40k, 40k-50k, Unlisted) - Strictly 100% Remote Only
    2. Part 2: Full-Time Engineering Jobs (10-15 LPA, 15-30 LPA, 30-45 LPA, 45-60 LPA, Unlisted) - Remote/On-site annotated
    3. Part 3: Negative Finding Audit (Closed / Zero Requisitions table)
    """
    lines = []
    lines.append(f"# 🎯 Job & Internship Harvest Report — {result.date_str}")
    lines.append("")
    lines.append(f"**Target Candidate:** [{PROFILE.name}]({PROFILE.portfolio_url}) • B.Tech CSE • Systems & Cloud Infrastructure Focus")
    lines.append(f"**Core Stack:** Go, Python, FastAPI, Docker, gVisor, Kubernetes, AWS, Terraform, Distributed Systems, CI/CD, DevSecOps, Vertex AI / LLMs")
    lines.append("")
    lines.append("> [!NOTE] **Filters & Invariants Enforced in Code:**")
    lines.append("> • **Internships:** Strictly 100% Remote Only (Worldwide or India Remote)")
    lines.append("> • **Full-Time Jobs:** Remote & India On-site Permitted (Explicitly annotated in location column)")
    lines.append("> • **Seniority Gating:** Hard exclusion of Senior, Staff, Principal, Lead, SDE2, and 3+ YOE management roles")
    lines.append("> • **Freshness:** Active posting cutoff (90 days for internships, 30 days for full-time)")
    lines.append(r"> • **Scoring:** Ranked 0–100 scale (Score $\ge 35$ for internships, $\ge 55$ for full-time; $\ge 75$ flagged as `⭐ Tier 1 Target`)")
    lines.append("> • **Verification:** 100% Direct Requisition Endpoints • HTTP 200 Confirmed • Zero Career Homepages")
    lines.append("> • **Anti-Monopoly:** Capped at at most 3 roles per company, ranked by technical score")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Map jobs to tiers
    tier_groups: Dict[PayTier, List[JobRequisition]] = {t: [] for t in PayTier}
    for j in result.active_jobs:
        tier_groups[j.pay_tier].append(j)

    # =========================================================================
    # PART 1: INTERNSHIPS
    # =========================================================================
    lines.append("## 🎓 Part 1: Internships")
    lines.append("*(Strictly 100% Remote Only — Worldwide Remote or India Remote for undergraduate attendance)*")
    lines.append("")

    intern_tiers = [
        ("### 🥉 Internships: ₹10,000 – ₹20,000 / month", PayTier.INTERN_10K_20K),
        ("### 🥈 Internships: ₹20,000 – ₹30,000 / month", PayTier.INTERN_20K_30K),
        ("### 🥇 Internships: ₹30,000 – ₹40,000 / month", PayTier.INTERN_30K_40K),
        ("### 💎 Internships: ₹40,000 – ₹50,000 / month", PayTier.INTERN_40K_50K),
        ("### 🚀 Venture-Backed Startups [Unlisted Stipend: Venture-Backed Competitive]", PayTier.INTERN_UNLISTED),
    ]

    for header, tier_key in intern_tiers:
        tier_items = [j for j in tier_groups.get(tier_key, []) if j.is_internship]
        lines.append(header)
        lines.append("")
        if tier_items:
            lines.append("| Score | Company | Role | Location | Stipend | Direct Application / Contact | Stack Match |")
            lines.append("|---|---|---|---|---|---|---|")
            for j in tier_items:
                score_badge = format_score_badge(j)
                link_cell = format_link_cell(j)
                loc_display = format_location(j)
                lines.append(f"| {score_badge} | **{j.company}** | {j.title} | {loc_display} | `{j.compensation_str}` | {link_cell} | {j.match_rationale} |")
        else:
            lines.append("*No active requisitions in this pay bracket for this scan.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # =========================================================================
    # PART 2: FULL-TIME ENGINEERING JOBS
    # =========================================================================
    lines.append("## 💼 Part 2: Full-Time Engineering Jobs")
    lines.append("*(Engineering positions open to early career / undergraduate candidates — Remote / On-site annotated in location column)*")
    lines.append("")

    job_tiers = [
        ("### 🥉 Full-Time: 10 – 15 LPA", PayTier.JOB_10_15_LPA),
        ("### 🥈 Full-Time: 15 – 30 LPA", PayTier.JOB_15_30_LPA),
        ("### 🥇 Full-Time: 30 – 45 LPA", PayTier.JOB_30_45_LPA),
        ("### 💎 Full-Time: 45+ LPA / Global USD", PayTier.JOB_45_60_LPA),
        ("### 🚀 Venture-Backed Startups [Unlisted Salary: Venture-Backed Competitive]", PayTier.JOB_UNLISTED),
    ]

    for header, tier_key in job_tiers:
        tier_items = [j for j in tier_groups.get(tier_key, []) if not j.is_internship]
        lines.append(header)
        lines.append("")
        if tier_items:
            lines.append("| Score | Company | Role | Location | Compensation | Direct Application / Contact | Stack Match |")
            lines.append("|---|---|---|---|---|---|---|")
            for j in tier_items:
                score_badge = format_score_badge(j)
                link_cell = format_link_cell(j)
                loc_display = format_location(j)
                lines.append(f"| {score_badge} | **{j.company}** | {j.title} | {loc_display} | `{j.compensation_str}` | {link_cell} | {j.match_rationale} |")
        else:
            lines.append("*No active requisitions in this pay bracket for this scan.*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # =========================================================================
    # PART 3: NEGATIVE FINDING AUDIT
    # =========================================================================
    lines.append("## 🛡️ Negative Finding Audit (Closed / Zero Requisitions Scanned)")
    lines.append("*(Per systems engineering invariants: Confirms scanned companies where no live engineering requisitions match candidate criteria. Never hypothesized.)*")
    lines.append("")

    if result.closed_companies:
        lines.append("| Scanned Company | Status | Notes |")
        lines.append("|---|---|---|")
        for comp in result.closed_companies:
            lines.append(f"| **{comp}** | `0 MATCHING ROLES` | No active engineering requisitions meeting stack & eligibility invariants |")
    else:
        lines.append("*All scanned targets had matching positions.*")

    lines.append("")
    lines.append(f"**Total Requisitions Scanned:** {result.total_scanned} | **Net-New Discovered:** {result.net_new_count} | **Verified Matches:** {len(result.active_jobs)}")
    lines.append("")

    funnel = result.internship_funnel or {}
    lines.append(
        f"> 📊 **Internship Funnel:** Seen: {funnel.get('seen', 0)} | "
        f"Dropped On-site: {funnel.get('dropped_onsite', 0)} | "
        f"Dropped Geo/Auth: {funnel.get('dropped_us_only', 0)} | "
        f"Dropped Stale (>90d): {funnel.get('dropped_stale', 0)} | "
        f"Dropped Low Score (<35): {funnel.get('dropped_low_score', 0)} | "
        f"Kept: {funnel.get('kept', 0)}"
    )
    lines.append("")
    return "\n".join(lines)
