import re
import xml.etree.ElementTree as ET
import httpx
from typing import List
from ..models import JobRequisition
from ..analyzer.text_extractor import clean_text

async def fetch_personio_jobs(client: httpx.AsyncClient, company_slug: str) -> List[JobRequisition]:
    """
    Personio XML Resolver:
    Tries .jobs.personio.de/xml?language=en then fallback to .jobs.personio.com/xml?language=en.
    Parses standard workzag-jobs XML structure.
    """
    urls = [
        f"https://{company_slug}.jobs.personio.de/xml?language=en",
        f"https://{company_slug}.jobs.personio.com/xml?language=en"
    ]

    xml_text = None
    successful_domain = "personio.de"
    for url in urls:
        try:
            res = await client.get(url, timeout=10.0)
            if res.status_code == 200 and ("xml" in res.headers.get("content-type", "").lower() or res.text.strip().startswith("<?xml")):
                xml_text = res.text
                successful_domain = "personio.de" if ".de" in url else "personio.com"
                break
        except Exception:
            continue

    if not xml_text:
        return []

    jobs = []
    try:
        root = ET.fromstring(xml_text)
        for pos in root.findall(".//position"):
            pos_id = pos.findtext("id", "")
            title = pos.findtext("name", "")
            office = pos.findtext("office", "Remote")
            employment_type = pos.findtext("employmentType", "")
            schedule = pos.findtext("schedule", "")

            # Location formatting
            location = office if office else "Remote"
            if "remote" in schedule.lower() and "remote" not in location.lower():
                location = f"{location} (Remote)"

            # Job description
            desc_parts = []
            job_desc = pos.find("jobDescriptions")
            if job_desc is not None:
                for d in job_desc.findall("jobDescription"):
                    name_header = d.findtext("name", "")
                    val_body = d.findtext("value", "")
                    desc_parts.append(f"{name_header}\n{val_body}")
            desc_text = clean_text("\n".join(desc_parts))

            is_internship = bool(
                re.search(r'\b(interns?|internships?|working\s*student|werkstudent|trainee)\b', title, re.I) or
                "intern" in employment_type.lower()
            )

            apply_url = f"https://{company_slug}.jobs.{successful_domain}/job/{pos_id}"
            posted_date = pos.findtext("createdAt", "")

            jobs.append(JobRequisition(
                id=str(pos_id),
                company=company_slug,
                title=title,
                location=location,
                apply_url=apply_url,
                description_text=desc_text,
                is_internship=is_internship,
                ats="Personio",
                posted_date=posted_date
            ))
    except Exception:
        pass

    return jobs
