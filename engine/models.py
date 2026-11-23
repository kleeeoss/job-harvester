from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

class PayTier(str, Enum):
    INTERN_10K_20K = "Internship: ₹10,000 – ₹20,000 / month"
    INTERN_20K_30K = "Internship: ₹20,000 – ₹30,000 / month"
    INTERN_30K_40K = "Internship: ₹30,000 – ₹40,000 / month"
    INTERN_40K_50K = "Internship: ₹40,000 – ₹50,000 / month"
    INTERN_UNLISTED = "[Unlisted Stipend: Venture-Backed Competitive]"
    JOB_10_15_LPA = "Full-Time: 10 – 15 LPA"
    JOB_15_30_LPA = "Full-Time: 15 – 30 LPA"
    JOB_30_45_LPA = "Full-Time: 30 – 45 LPA"
    JOB_45_60_LPA = "Full-Time: 45 – 60 LPA"
    JOB_UNLISTED = "[Unlisted Salary: Venture-Backed Competitive]"

@dataclass
class JobRequisition:
    id: str
    company: str
    title: str
    location: str
    apply_url: str
    description_text: str = ""
    is_internship: bool = False
    pay_tier: PayTier = PayTier.JOB_UNLISTED
    compensation_str: str = "[Unlisted Salary: Venture-Backed Competitive]"
    location_type: str = "India / Remote"
    is_top_tier: bool = False
    is_verified: bool = False
    match_rationale: str = ""
    ats: str = "Direct ATS"
    posted_date: str = ""
    score: int = 0
    tech_score: int = 0
    is_tier_1: bool = False
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    contact_email: Optional[str] = None
    hn_permalink: Optional[str] = None

    def __post_init__(self):
        if self.tech_score and not self.score:
            self.score = self.tech_score
        elif self.score and not self.tech_score:
            self.tech_score = self.score

@dataclass
class HarvestResult:
    date_str: str
    active_jobs: List[JobRequisition] = field(default_factory=list)
    closed_companies: List[str] = field(default_factory=list)
    total_scanned: int = 0
    net_new_count: int = 0
    internship_funnel: Dict[str, int] = field(default_factory=dict)
