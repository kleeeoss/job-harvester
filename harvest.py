import argparse
import asyncio
import os
import sys
from datetime import datetime

from config.settings import DEFAULT_MAX_ROLES_PER_COMPANY, DEFAULT_HARVEST_LIMIT
from engine.harvester import JobHarvester
from engine.output.markdown_gen import generate_harvest_report

def main():
    parser = argparse.ArgumentParser(
        description="Job Harvester V3: Stateful Multi-ATS & Founder Outreach Engine for Garv Vaidya."
    )
    parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="Filter to a specific company by name or slug (e.g. 'sarvam', 'modal', 'razorpay')."
    )
    parser.add_argument(
        "--quick", "--fast",
        action="store_true",
        help="Quick execution mode (scans top 10 target companies)."
    )
    parser.add_argument(
        "--feed",
        action="store_true",
        default=True,
        help="Enable live stream ingestion from SimplifyJobs & Hacker News (default: True)."
    )
    parser.add_argument(
        "--no-feed",
        action="store_false",
        dest="feed",
        help="Disable live stream ingestion."
    )
    parser.add_argument(
        "--no-cap",
        action="store_true",
        help="Disable the anti-monopoly 3-role-per-company limit."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Resurface all historical matched jobs instead of only net-new positions."
    )
    parser.add_argument(
        "--include-discovered",
        action="store_true",
        help="Scan up to 100 auto-discovered ATS companies persisted in SQLite from previous feed runs."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_HARVEST_LIMIT,
        help=f"Maximum number of verified positions to extract (default: {DEFAULT_HARVEST_LIMIT})."
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip live HTTP link verification for raw external links."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output file path for the generated markdown report."
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 JOB HARVESTER V3 — Candidate: Garv Vaidya (Systems, Cloud & Backend Engine)")
    print("Invariants: 100% Direct Links | SQLite Stateful | Anti-Monopoly | 0-100 Ranked")
    print("=" * 80)

    harvester = JobHarvester()
    max_companies = 10 if args.quick else None
    max_roles_per_company = None if args.no_cap else DEFAULT_MAX_ROLES_PER_COMPANY

    print(f"[*] Configuration: Quick={args.quick}, Feeds={args.feed}, Anti-Monopoly Cap={max_roles_per_company}, Limit={args.limit}, Verify={not args.no_verify}, All={args.all}, Discovered={args.include_discovered}")
    print("[*] Launching high-throughput concurrent harvester with SQLite persistence...")

    result = asyncio.run(
        harvester.run(
            filter_company=args.company,
            max_companies=max_companies,
            verify_links=not args.no_verify,
            enable_feeds=args.feed,
            max_roles_per_company=max_roles_per_company,
            limit=args.limit,
            output_all_unreported=not args.all,
            include_discovered=args.include_discovered
        )
    )

    report_md = generate_harvest_report(result)

    # Determine report save path
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = args.output or os.path.join(reports_dir, f"harvest_{result.date_str}.md")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n" + "=" * 80)
    print("✅ HARVEST COMPLETED SUCCESSFULLY")
    print(f"• Total Raw Requisitions Scanned: {result.total_scanned}")
    print(f"• Net-New Roles Discovered & Persisted: {result.net_new_count}")
    print(f"• Invariant-Verified Active Positions: {len(result.active_jobs)}")
    print(f"• Scanned Companies with Closed/Zero Listings: {len(result.closed_companies)}")
    print(f"• Generated Report Saved To: {report_file}")
    print("=" * 80)

    if result.active_jobs:
        print(f"\n🌟 Top Matching Requisitions (Showing first 15 of {len(result.active_jobs)}):")
        for idx, job in enumerate(result.active_jobs[:15], 1):
            role_type = "Internship" if job.is_internship else "Full-Time"
            tier1_badge = " [⭐ Tier 1 Target]" if (job.is_tier_1 or job.score >= 75) else ""
            print(f"  {idx}. [{job.company}] {job.title} ({role_type}) — Score: {job.score}{tier1_badge}")
            print(f"     Location: {job.location} ({job.location_type})")
            print(f"     Pay Tier: {job.pay_tier.value}")
            print(f"     Direct Link: {job.apply_url}")
            print(f"     Stack Match: {job.match_rationale}\n")
    else:
        print("\n[*] Zero net-new active requisitions matched all criteria in this run.")

if __name__ == "__main__":
    main()
