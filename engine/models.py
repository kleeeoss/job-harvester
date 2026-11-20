from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

class PayTier(str, Enum):
    INTERN_10K_20K = "Internship: ₹10,000 – ₹20,000 / month"
    INTERN_20K_30K = "Internship: ₹20,000 – ₹30,000 / month"
    INTERN_30K_50K = "Internship: ₹30,000 – ₹50,000 / month"
    JOB_10_15_LPA = "Full-Time: 10 – 15 LPA"
    JOB_15_30_LPA = "Full-Time: 15 – 30 LPA"
    JOB_30_60_LPA = "Full-Time: 30 – 60 LPA"
    UNLISTED = "[Unlisted Salary: Venture-Backed Competitive]"

@dataclass
class JobRequisition:
    id: str
    company: str
    title: str
    location: str
    apply_url: str
    description_text: str
    is_internship: bool = False
    pay_tier: PayTier = PayTier.UNLISTED
    compensation_str: str = "[Unlisted Salary: Venture-Backed Competitive]"
    location_type: str = "India / Remote"
    is_top_tier: bool = False
    is_verified: bool = False
    match_rationale: str = ""
    ats: str = "Direct ATS"
    posted_date: str = ""

@dataclass
class HarvestResult:
    date_str: str
    active_jobs: List[JobRequisition] = field(default_factory=list)
    closed_companies: List[str] = field(default_factory=list)
    total_scanned: int = 0
