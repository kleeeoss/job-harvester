import argparse
import asyncio
import os
import sys
from datetime import datetime

from engine.harvester import JobHarvester
from engine.output.markdown_gen import generate_harvest_report

def main():
    parser = argparse.ArgumentParser(
        description="Job Harvester: Automated Invariant-Enforcing Job & Internship Harvester for Garv Vaidya."
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
        help="Quick execution mode (scans top 6 target companies)."
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip live HTTP link verification (useful for offline testing)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output file path for the generated markdown report."
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🚀 JOB HARVESTER — Candidate: Garv Vaidya (Class of 2027, CGPA 7.17)")
    print("Invariants: 100% Direct Links | Pay Tiers | Strict Batch & GPA Safe")
    print("=" * 70)

    harvester = JobHarvester()
    max_companies = 6 if args.quick else None

    print(f"[*] Starting harvest run (Quick mode: {args.quick}, Verify links: {not args.no_verify})...")
    result = asyncio.run(
        harvester.run(
            filter_company=args.company,
            max_companies=max_companies,
            verify_links=not args.no_verify
        )
    )

    report_md = generate_harvest_report(result)

    # Determine report save path
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_file = args.output or os.path.join(reports_dir, f"harvest_{result.date_str}.md")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n" + "=" * 70)
    print(f"✅ HARVEST COMPLETED SUCCESSFULLY")
    print(f"• Total Raw Requisitions Scanned: {result.total_scanned}")
    print(f"• Invariant-Verified Active Positions: {len(result.active_jobs)}")
    print(f"• Scanned Companies with Closed/Zero Listings: {len(result.closed_companies)}")
    print(f"• Generated Report Saved To: {report_file}")
    print("=" * 70)

    if result.active_jobs:
        print("\n🌟 Discovered Matching Requisitions:")
        for idx, job in enumerate(result.active_jobs, 1):
            role_type = "Internship" if job.is_internship else "Full-Time"
            print(f"  {idx}. [{job.company}] {job.title} ({role_type})")
            print(f"     Location: {job.location}")
            print(f"     Pay Tier: {job.pay_tier.value}")
            print(f"     Direct Link: {job.apply_url}")
            print(f"     Stack: {job.match_rationale}\n")
    else:
        print("\n[*] Zero active requisitions matched all criteria in this run.")

if __name__ == "__main__":
    main()
