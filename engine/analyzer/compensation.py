import re
from typing import Tuple
from ..models import PayTier
from .text_extractor import clean_text

RE_UNPAID = re.compile(
    r'\b(unpaid|for\s*college\s*credit|no\s*stipend|zero\s*stipend|0\s*/\s*mo|for\s*experience\s*only)\b',
    re.IGNORECASE
)

# INR Stipend Regex (e.g. ₹15,000 / month, 25,000 INR pm, 10k/month, 45,000/month, stipend is 15,000)
RE_INR_STIPEND = re.compile(
    r'(?:stipend\s*(?:is|:|of)?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,2}),?([0-9]{3})\s*(?:-|to)?\s*(?:(?:₹|rs\.?|inr)?\s*([0-9]{1,2}),?([0-9]{3}))?\s*(?:/\s*(?:mo|month)|per\s*month|pm|stipend|inr|monthly)',
    re.IGNORECASE
)
RE_INR_K_STIPEND = re.compile(
    r'(?:₹|rs\.?|inr)?\s*([1-9][0-9])\s*k\s*(?:-|to)?\s*(?:[0-9]{1,2}\s*k)?\s*(?:/mo|per\s*month|pm|stipend|monthly)?',
    re.IGNORECASE
)

# USD Monthly Stipend (e.g. $1,500/mo, $500 per month)
RE_USD_STIPEND = re.compile(
    r'\$\s*([0-9]{1,2}),?([0-9]{3})\s*(?:/mo|per\s*month|monthly)?',
    re.IGNORECASE
)

# LPA Salary Regex (e.g. 12 - 14 LPA, 22 - 28 LPA, 45 LPA to 55 LPA, 5 to 7 LPA)
RE_LPA_SALARY = re.compile(
    r'(?:ctc:?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*(?:-|to)?\s*([0-9]{1,2}(?:\.[0-9]+)?)?\s*lpa',
    re.IGNORECASE
)

# USD Annual Salary (e.g. $120,000 - $150,000, $80k - $120k)
RE_USD_ANNUAL_K = re.compile(
    r'\$\s*([0-9]{2,3})\s*k\b',
    re.IGNORECASE
)
RE_USD_ANNUAL_FULL = re.compile(
    r'\$\s*([0-9]{2,3}),([0-9]{3})\b',
    re.IGNORECASE
)

def parse_compensation(job_text: str, is_internship: bool = False) -> Tuple[bool, PayTier, str, str]:
    """
    Parses compensation from job text and categorizes into PayTier:
    Internships:
      - >= ₹10,000/month minimum (reject if below or unpaid)
      - Tiers: 10k-20k, 20k-30k, 30k-50k (cap at 50k)
    Full-time:
      - >= 10 LPA minimum (reject if below)
      - Tiers: 10-15 LPA, 15-30 LPA, 30-60 LPA (cap at 60 LPA)
    Unlisted:
      - Venture-backed competitive fallback
    """
    text = clean_text(job_text)

    if is_internship:
        # Check unpaid
        if RE_UNPAID.search(text):
            return False, PayTier.UNLISTED, "₹0/mo", "Internship rejected: Explicitly unpaid"

        # Check INR stipend
        match_inr = RE_INR_STIPEND.search(text)
        if match_inr:
            low_amount = int(f"{match_inr.group(1)}{match_inr.group(2)}")
            high_amount = int(f"{match_inr.group(3)}{match_inr.group(4)}") if match_inr.group(3) else low_amount
            comp_display = f"₹{low_amount:,} - ₹{high_amount:,}/mo" if high_amount != low_amount else f"₹{low_amount:,}/mo"

            if low_amount < 10000 and high_amount < 10000:
                return False, PayTier.UNLISTED, comp_display, f"Internship stipend ₹{low_amount}/mo below ₹10k threshold"

            # Assign tier based on low_amount (or high if low < 10k)
            effective_amount = low_amount if low_amount >= 10000 else high_amount
            if effective_amount < 20000:
                tier = PayTier.INTERN_10K_20K
            elif effective_amount < 30000:
                tier = PayTier.INTERN_20K_30K
            else:
                tier = PayTier.INTERN_30K_50K

            return True, tier, comp_display, f"Verified Stipend: {comp_display}"

        # Check USD stipend (assume 1 USD ~ 83 INR)
        match_usd = RE_USD_STIPEND.search(text)
        if match_usd and any(k in text.lower() for k in ["intern", "stipend", "month"]):
            usd_amount = int(f"{match_usd.group(1)}{match_usd.group(2)}")
            inr_equiv = usd_amount * 83
            comp_display = f"${usd_amount:,}/mo (~₹{inr_equiv:,}/mo)"
            if inr_equiv < 10000:
                return False, PayTier.UNLISTED, comp_display, f"Internship stipend ${usd_amount}/mo below ₹10k threshold"
            if inr_equiv < 20000:
                tier = PayTier.INTERN_10K_20K
            elif inr_equiv < 30000:
                tier = PayTier.INTERN_20K_30K
            else:
                tier = PayTier.INTERN_30K_50K
            return True, tier, comp_display, f"Verified Stipend: {comp_display}"

        # Unlisted stipend fallback for VC startups
        return True, PayTier.UNLISTED, "[Unlisted Salary: Venture-Backed Competitive]", "Stipend Unlisted (Venture-Backed Competitive)"

    else:
        # Full-time job compensation check
        match_lpa = RE_LPA_SALARY.search(text)
        if match_lpa:
            min_lpa = float(match_lpa.group(1))
            max_lpa = float(match_lpa.group(2)) if match_lpa.group(2) else min_lpa
            comp_display = f"{min_lpa:.0f} - {max_lpa:.0f} LPA" if max_lpa != min_lpa else f"{min_lpa:.0f} LPA"

            if min_lpa < 10.0 and max_lpa < 10.0:
                return False, PayTier.UNLISTED, comp_display, f"Job salary {min_lpa} LPA below 10 LPA threshold"

            effective_lpa = min_lpa if min_lpa >= 10.0 else max_lpa
            if effective_lpa < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif effective_lpa < 30.0:
                tier = PayTier.JOB_15_30_LPA
            else:
                tier = PayTier.JOB_30_60_LPA

            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # Check USD annual compensation (1 USD ~ 83 INR, $12k USD/yr ~ 10 LPA)
        match_usd_k = RE_USD_ANNUAL_K.search(text)
        if match_usd_k:
            k_val = int(match_usd_k.group(1))
            lpa_equiv = (k_val * 1000 * 83) / 100000.0  # LPA
            comp_display = f"${k_val}k USD/yr (~{lpa_equiv:.0f} LPA)"
            if lpa_equiv < 10.0:
                return False, PayTier.UNLISTED, comp_display, f"Salary below 10 LPA threshold"
            if lpa_equiv < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif lpa_equiv < 30.0:
                tier = PayTier.JOB_15_30_LPA
            else:
                tier = PayTier.JOB_30_60_LPA
            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # Unlisted salary fallback for VC startups
        return True, PayTier.UNLISTED, "[Unlisted Salary: Venture-Backed Competitive]", "Salary Unlisted (Venture-Backed Competitive)"
