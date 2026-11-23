import re
from typing import Tuple
from ..models import PayTier
from .text_extractor import clean_text

RE_UNPAID = re.compile(
    r'\b(unpaid|for\s*college\s*credit|no\s*stipend|zero\s*stipend|0\s*/\s*mo|for\s*experience\s*only)\b',
    re.IGNORECASE
)

# INR Full-digit Stipend Regex (e.g. ₹15,000 / month, 25,000 INR pm, 45,000/month)
RE_INR_STIPEND = re.compile(
    r'(?:stipend\s*(?:is|:|of)?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,2}),?([0-9]{3})\s*(?:-|to)?\s*(?:(?:₹|rs\.?|inr)?\s*([0-9]{1,2}),?([0-9]{3}))?\s*(?:/\s*(?:mo|month)|per\s*month|pm|stipend|inr|monthly|/-)',
    re.IGNORECASE
)

# INR 'k' notation Stipend (e.g. 25k/month, ₹20k - ₹30k pm, stipend: 35k)
RE_INR_K_STIPEND = re.compile(
    r'(?:stipend\s*(?:is|:|of)?\s*)?(?:₹|rs\.?|inr)?\s*([1-9][0-9]?)\s*k\s*(?:-|to)?\s*(?:(?:₹|rs\.?|inr)?\s*([1-9][0-9]?)\s*k)?\s*(?:/\s*(?:mo|month)|per\s*month|pm|stipend|monthly)\b',
    re.IGNORECASE
)

# USD / Foreign Monthly Stipend (e.g. $1,500/mo, $500 per month, €1,200/mo)
RE_USD_STIPEND = re.compile(
    r'(?:\$|€|£)\s*([0-9]{1,2}),?([0-9]{3})\s*(?:-|to)?\s*(?:(?:\$|€|£)?\s*([0-9]{1,2}),?([0-9]{3}))?\s*(?:/\s*(?:mo|month)|per\s*month|monthly)?',
    re.IGNORECASE
)

# LPA Salary Regex (e.g. 12 - 14 LPA, 22 - 28 LPA, 45 LPA to 55 LPA, 5 to 7 LPA)
RE_LPA_SALARY = re.compile(
    r'(?:ctc:?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*(?:-|to)?\s*([0-9]{1,2}(?:\.[0-9]+)?)?\s*lpa\b',
    re.IGNORECASE
)

# Lakhs Salary Regex (e.g. 12 Lakhs, 15 - 20 Lakhs per annum)
RE_LAKHS_SALARY = re.compile(
    r'(?:ctc:?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,2}(?:\.[0-9]+)?)\s*(?:-|to)?\s*([0-9]{1,2}(?:\.[0-9]+)?)?\s*(?:lakhs?|lacs?)\b',
    re.IGNORECASE
)

# USD / Foreign Full Annual Salary (e.g. $120,000 - $150,000 / year, base salary $130,000)
RE_USD_ANNUAL_FULL = re.compile(
    r'(?:\b(?:salary|base|compensation|pay|ctc)\s*(?:is|:|of)?\s*)?(?:\$|€|£)\s*([0-9]{2,3}),([0-9]{3})\s*(?:-|to)?\s*(?:(?:\$|€|£)?\s*([0-9]{2,3}),([0-9]{3}))?\s*(?:/\s*(?:yr|year)|per\s*year|annually)?',
    re.IGNORECASE
)

# USD Annual 'k' format with salary context (e.g. $120k - $150k, salary $100k, $120k/yr)
RE_USD_ANNUAL_K = re.compile(
    r'(?:\b(?:salary|base|compensation|pay|ctc)\s*(?:is|:|of)?\s*)?(?:\$|€|£)\s*([0-9]{2,3})\s*k\s*(?:-|to)?\s*(?:(?:\$|€|£)?\s*([0-9]{2,3})\s*k)?\s*(?:/\s*(?:yr|year)|per\s*year|annually)?',
    re.IGNORECASE
)

# Hourly Rate Regex (e.g. $50/hr, $40 - $60 per hour)
RE_HOURLY_RATE = re.compile(
    r'(?:\b(?:pay|rate|salary)\s*(?:is|:|of)?\s*)?(?:\$|€|£)\s*([0-9]{2,3})\s*(?:-|to)?\s*(?:(?:\$|€|£)?\s*([0-9]{2,3}))?\s*(?:/\s*hr|per\s*hour|hourly)\b',
    re.IGNORECASE
)

def parse_compensation(job_text: str, is_internship: bool = False) -> Tuple[bool, PayTier, str, str]:
    """
    Parses compensation from job text and categorizes into PayTier:
    Internships:
      - >= ₹10,000/month minimum (reject if below or unpaid)
      - Tiers: 10k-20k, 20k-30k, 30k-40k, 40k-50k (cap at 50k)
      - Unlisted: [Unlisted Stipend: Venture-Backed Competitive]
    Full-time:
      - >= 10 LPA minimum (reject if below)
      - Tiers: 10-15 LPA, 15-30 LPA, 30-45 LPA, 45-60 LPA (cap at 60 LPA)
      - Unlisted: [Unlisted Salary: Venture-Backed Competitive]
    """
    text = clean_text(job_text)

    if is_internship:
        # Check unpaid
        if RE_UNPAID.search(text):
            return False, PayTier.INTERN_UNLISTED, "₹0/mo", "Internship rejected: Explicitly unpaid"

        # 1. Check INR full digits stipend (e.g. ₹15,000 / month)
        match_inr = RE_INR_STIPEND.search(text)
        if match_inr:
            low_amount = int(f"{match_inr.group(1)}{match_inr.group(2)}")
            high_amount = int(f"{match_inr.group(3)}{match_inr.group(4)}") if match_inr.group(3) else low_amount
            comp_display = f"₹{low_amount:,} - ₹{high_amount:,}/mo" if high_amount != low_amount else f"₹{low_amount:,}/mo"

            if low_amount < 10000 and high_amount < 10000:
                return False, PayTier.INTERN_UNLISTED, comp_display, f"Internship stipend ₹{low_amount}/mo below ₹10k threshold"

            effective_amount = low_amount if low_amount >= 10000 else high_amount
            if effective_amount < 20000:
                tier = PayTier.INTERN_10K_20K
            elif effective_amount < 30000:
                tier = PayTier.INTERN_20K_30K
            elif effective_amount < 40000:
                tier = PayTier.INTERN_30K_40K
            else:
                tier = PayTier.INTERN_40K_50K

            return True, tier, comp_display, f"Verified Stipend: {comp_display}"

        # 2. Check INR 'k' notation stipend (e.g. 25k/month)
        match_k = RE_INR_K_STIPEND.search(text)
        if match_k:
            low_amount = int(match_k.group(1)) * 1000
            high_amount = int(match_k.group(2)) * 1000 if match_k.group(2) else low_amount
            comp_display = f"₹{low_amount:,} - ₹{high_amount:,}/mo" if high_amount != low_amount else f"₹{low_amount:,}/mo"

            if low_amount < 10000 and high_amount < 10000:
                return False, PayTier.INTERN_UNLISTED, comp_display, f"Internship stipend ₹{low_amount}/mo below ₹10k threshold"

            effective_amount = low_amount if low_amount >= 10000 else high_amount
            if effective_amount < 20000:
                tier = PayTier.INTERN_10K_20K
            elif effective_amount < 30000:
                tier = PayTier.INTERN_20K_30K
            elif effective_amount < 40000:
                tier = PayTier.INTERN_30K_40K
            else:
                tier = PayTier.INTERN_40K_50K

            return True, tier, comp_display, f"Verified Stipend: {comp_display}"

        # 3. Check USD/Foreign monthly stipend (assume 1 USD ~ 83 INR)
        match_usd = RE_USD_STIPEND.search(text)
        if match_usd and any(k in text.lower() for k in ["intern", "stipend", "month"]):
            usd_amount = int(f"{match_usd.group(1)}{match_usd.group(2)}")
            inr_equiv = usd_amount * 83
            comp_display = f"${usd_amount:,}/mo (~₹{inr_equiv:,}/mo)"
            if inr_equiv < 10000:
                return False, PayTier.INTERN_UNLISTED, comp_display, f"Internship stipend ${usd_amount}/mo below ₹10k threshold"
            if inr_equiv < 20000:
                tier = PayTier.INTERN_10K_20K
            elif inr_equiv < 30000:
                tier = PayTier.INTERN_20K_30K
            elif inr_equiv < 40000:
                tier = PayTier.INTERN_30K_40K
            else:
                tier = PayTier.INTERN_40K_50K
            return True, tier, comp_display, f"Verified Stipend: {comp_display}"

        # Unlisted stipend fallback for VC startups
        return True, PayTier.INTERN_UNLISTED, "[Unlisted Stipend: Venture-Backed Competitive]", "Stipend Unlisted (Venture-Backed Competitive)"

    else:
        # Full-time job compensation check
        # 1. Check LPA salary
        match_lpa = RE_LPA_SALARY.search(text)
        if match_lpa:
            min_lpa = float(match_lpa.group(1))
            max_lpa = float(match_lpa.group(2)) if match_lpa.group(2) else min_lpa
            comp_display = f"{min_lpa:.0f} - {max_lpa:.0f} LPA" if max_lpa != min_lpa else f"{min_lpa:.0f} LPA"

            if min_lpa < 10.0 and max_lpa < 10.0:
                return False, PayTier.JOB_UNLISTED, comp_display, f"Job salary {min_lpa} LPA below 10 LPA threshold"

            effective_lpa = min_lpa if min_lpa >= 10.0 else max_lpa
            if effective_lpa < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif effective_lpa < 30.0:
                tier = PayTier.JOB_15_30_LPA
            elif effective_lpa < 45.0:
                tier = PayTier.JOB_30_45_LPA
            else:
                tier = PayTier.JOB_45_60_LPA

            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # 2. Check Lakhs salary
        match_lakhs = RE_LAKHS_SALARY.search(text)
        if match_lakhs:
            min_lpa = float(match_lakhs.group(1))
            max_lpa = float(match_lakhs.group(2)) if match_lakhs.group(2) else min_lpa
            comp_display = f"{min_lpa:.0f} - {max_lpa:.0f} Lakhs" if max_lpa != min_lpa else f"{min_lpa:.0f} Lakhs"

            if min_lpa < 10.0 and max_lpa < 10.0:
                return False, PayTier.JOB_UNLISTED, comp_display, f"Job salary {min_lpa} Lakhs below 10 LPA threshold"

            effective_lpa = min_lpa if min_lpa >= 10.0 else max_lpa
            if effective_lpa < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif effective_lpa < 30.0:
                tier = PayTier.JOB_15_30_LPA
            elif effective_lpa < 45.0:
                tier = PayTier.JOB_30_45_LPA
            else:
                tier = PayTier.JOB_45_60_LPA

            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # 3. Check USD full annual compensation ($120,000 - $150,000 / year)
        match_usd_full = RE_USD_ANNUAL_FULL.search(text)
        has_salary_context = any(w in text.lower() for w in ["salary", "base", "compensation", "pay", "/yr", "/year", "per year", "annual"])
        if match_usd_full and (has_salary_context or "-" in match_usd_full.group(0)):
            val1 = int(f"{match_usd_full.group(1)}{match_usd_full.group(2)}")
            val2 = int(f"{match_usd_full.group(3)}{match_usd_full.group(4)}") if match_usd_full.group(3) else val1
            lpa_equiv1 = (val1 * 83) / 100000.0
            lpa_equiv2 = (val2 * 83) / 100000.0
            comp_display = f"${val1:,} - ${val2:,}/yr (~{lpa_equiv1:.0f} - {lpa_equiv2:.0f} LPA)" if val2 != val1 else f"${val1:,}/yr (~{lpa_equiv1:.0f} LPA)"

            if lpa_equiv1 < 10.0 and lpa_equiv2 < 10.0:
                return False, PayTier.JOB_UNLISTED, comp_display, f"Salary below 10 LPA threshold"

            effective_lpa = lpa_equiv1 if lpa_equiv1 >= 10.0 else lpa_equiv2
            if effective_lpa < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif effective_lpa < 30.0:
                tier = PayTier.JOB_15_30_LPA
            elif effective_lpa < 45.0:
                tier = PayTier.JOB_30_45_LPA
            else:
                tier = PayTier.JOB_45_60_LPA
            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # 4. Check USD annual 'k' compensation ($120k - $150k)
        match_usd_k = RE_USD_ANNUAL_K.search(text)
        if match_usd_k and (has_salary_context or "-" in match_usd_k.group(0)):
            k_val1 = int(match_usd_k.group(1))
            k_val2 = int(match_usd_k.group(2)) if match_usd_k.group(2) else k_val1
            lpa_equiv1 = (k_val1 * 1000 * 83) / 100000.0
            lpa_equiv2 = (k_val2 * 1000 * 83) / 100000.0
            comp_display = f"${k_val1}k - ${k_val2}k/yr (~{lpa_equiv1:.0f} - {lpa_equiv2:.0f} LPA)" if k_val2 != k_val1 else f"${k_val1}k USD/yr (~{lpa_equiv1:.0f} LPA)"

            if lpa_equiv1 < 10.0 and lpa_equiv2 < 10.0:
                return False, PayTier.JOB_UNLISTED, comp_display, f"Salary below 10 LPA threshold"

            effective_lpa = lpa_equiv1 if lpa_equiv1 >= 10.0 else lpa_equiv2
            if effective_lpa < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif effective_lpa < 30.0:
                tier = PayTier.JOB_15_30_LPA
            elif effective_lpa < 45.0:
                tier = PayTier.JOB_30_45_LPA
            else:
                tier = PayTier.JOB_45_60_LPA
            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # 5. Check hourly compensation ($50/hr)
        match_hr = RE_HOURLY_RATE.search(text)
        if match_hr:
            rate = int(match_hr.group(1))
            annual_usd = rate * 2000
            lpa_equiv = (annual_usd * 83) / 100000.0
            comp_display = f"${rate}/hr (~{lpa_equiv:.0f} LPA)"

            if lpa_equiv < 10.0:
                return False, PayTier.JOB_UNLISTED, comp_display, f"Hourly rate below 10 LPA threshold"

            if lpa_equiv < 15.0:
                tier = PayTier.JOB_10_15_LPA
            elif lpa_equiv < 30.0:
                tier = PayTier.JOB_15_30_LPA
            elif lpa_equiv < 45.0:
                tier = PayTier.JOB_30_45_LPA
            else:
                tier = PayTier.JOB_45_60_LPA
            return True, tier, comp_display, f"Verified Salary: {comp_display}"

        # Unlisted salary fallback for VC startups
        return True, PayTier.JOB_UNLISTED, "[Unlisted Salary: Venture-Backed Competitive]", "Salary Unlisted (Venture-Backed Competitive)"
