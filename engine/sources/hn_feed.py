import html
import re
import httpx
from typing import List, Tuple, Dict, Any, Optional
from ..models import JobRequisition, PayTier
from ..analyzer.text_extractor import clean_text
from ..database import generate_job_id

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=Who%20is%20hiring&hitsPerPage=5"
HN_ITEM_URL = "https://hn.algolia.com/api/v1/items/{item_id}"

RE_ATS_DOMAINS = re.compile(
    r'(?:jobs\.ashbyhq\.com|app\.ashbyhq\.com|boards\.greenhouse\.io|job-boards\.greenhouse\.io|'
    r'jobs\.lever\.co|api\.eu\.lever\.co|apply\.workable\.com|ats\.rippling\.com|'
    r'jobs\.smartrecruiters\.com|api\.gem\.com|[a-zA-Z0-9_\-\.]+\.jobs\.personio\.(?:de|com)|'
    r'[a-zA-Z0-9_\-\.]+\.recruitee\.com|[a-zA-Z0-9_\-\.]+\.myworkdayjobs\.com)',
    re.I
)

def extract_comment_links(comment_html: str) -> List[str]:
    """
    Extracts complete, unescaped ATS URLs from comment HTML.
    Prefers href attributes over text bodies to avoid truncated '...' URLs.
    """
    unescaped = html.unescape(comment_html)
    hrefs = re.findall(r'href=["\'](https?://[^"\'>\s]+)["\']', unescaped, re.I)
    raw_urls = re.findall(r'(https?://[^\s"\'<>]+)', unescaped, re.I)

    candidate_links = hrefs if hrefs else raw_urls
    all_links = []
    seen = set()
    for link in candidate_links:
        clean = link.rstrip(".,);]>'\"")
        if clean.endswith("...") or clean.endswith(".."):
            continue
        if RE_ATS_DOMAINS.search(clean) and clean not in seen:
            seen.add(clean)
            all_links.append(clean)
    return all_links

def extract_founder_emails(text: str) -> List[str]:
    """
    Extracts direct and obfuscated founder/team contact emails from HN comments.
    Supports 'founder@startup.ai', 'eng [at] company dot com', 'jobs (at) domain.co.uk'.
    Guards against false-positives like 'platform.io' by requiring whitespace around bare 'at' and 'dot'.
    """
    found = []
    # 1. Direct emails
    directs = re.findall(r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b', text)
    for d in directs:
        d_clean = d.strip('.').lower()
        if not d_clean.endswith(('png', 'jpg', 'svg', 'js', 'css')):
            found.append(d_clean)

    # 2. Obfuscated emails
    pattern = r'\b([a-zA-Z0-9_.+-]+)(?:\s*(?:\[at\]|\(at\))\s*|\s+at\s+)([a-zA-Z0-9-]+(?:\s*(?:\[dot\]|\(dot\)|\.)\s*[a-zA-Z0-9-]+|\s+dot\s+[a-zA-Z0-9-]+)+)\b'
    matches = re.findall(pattern, text, re.I)
    for user, domain_raw in matches:
        if domain_raw.startswith('http') or domain_raw.startswith('www'):
            continue
        domain_clean = re.sub(r'\s*(?:\[dot\]|\(dot\))\s*|\s+dot\s+', '.', domain_raw).strip('.')
        if '.' in domain_clean and not any(k in domain_clean for k in [' ', '/', ':', ';']):
            tld = domain_clean.split('.')[-1]
            if len(tld) >= 2:
                found.append(f"{user}@{domain_clean}".lower())

    return list(dict.fromkeys(found))

RE_JOB_SEEKER = re.compile(
    r'\b('
    r'seeking\s+(?:a\s+)?(?:role|position|job|internship|work|opportunity)|'
    r'looking\s+for\s+(?:a\s+)?(?:role|position|job|internship|work|opportunity)|'
    r'available\s+for\s+(?:hire|work|roles?|freelance)|available\s+immediately|'
    r'my\s+resume|hire\s+me|open\s+to\s+work'
    r')\b',
    re.IGNORECASE
)

RE_HIRING_INTENT = re.compile(
    r'\b('
    r"we\s*(?:are|'re)\s*hiring|join\s+(?:our\s+)?team|looking\s+to\s+hire|"
    r'looking\s+for\s+(?:a\s+)?(?:software|backend|systems?|full\s*stack|engineer|developer|intern)|'
    r'apply\s+at|reach\s+out\s+at|contact\s+us|email\s+us|hiring\s+for'
    r')\b',
    re.IGNORECASE
)

PERSONAL_WEBMAILS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "icloud.com", "aol.com", "zoho.com"
}

def parse_hn_comment(comment_html: str, comment_id: Optional[str] = None) -> List[JobRequisition]:
    """
    Parses a top-level HN 'Who is hiring' comment:
    1. Extracts direct ATS URLs and links.
    2. If no ATS link is present, extracts founder emails and tags as DIRECT_FOUNDER_EMAIL.
    """
    unescaped = html.unescape(comment_html)
    clean = clean_text(unescaped)
    if not clean:
        return []

    # 0. Reject job seekers immediately
    if RE_JOB_SEEKER.search(clean):
        return []

    # Convert <p>, </p>, <br>, <br/> to newline before text cleaning to preserve line headers
    text_with_newlines = re.sub(r'</p>|<br\s*/?>', '\n', unescaped, flags=re.I)
    text_with_newlines = re.sub(r'<p\b[^>]*>', '\n', text_with_newlines, flags=re.I)

    raw_lines = [l.strip() for l in text_with_newlines.split("\n") if l.strip()]
    first_line_raw = raw_lines[0] if raw_lines else ""
    first_line = clean_text(first_line_raw)

    # Parse standard HN first line header: Company | Role | Location | Remote/Onsite
    parts = [p.strip() for p in first_line.split("|")]
    has_pipes = len(parts) >= 2 and len(parts[0]) <= 50

    base_company = parts[0] if has_pipes else ""
    base_title = parts[1] if has_pipes and len(parts) >= 2 else ""
    base_location = parts[2] if has_pipes and len(parts) >= 3 else ""

    is_remote_mentioned = bool(re.search(r'\b(remote|work\s*from\s*home|wfh|anywhere|worldwide)\b', clean, re.I))

    # Find direct ATS URLs in the comment
    links = extract_comment_links(comment_html)
    jobs = []
    hn_link = f"https://news.ycombinator.com/item?id={comment_id}" if comment_id else None

    # Map each link to its preceding title if present in raw HTML
    link_titles = {}
    title_matches = re.findall(r'([^<>\n\r]{3,100}?)\s*[-–—:•]?\s*<a\s+[^>]*?href=["\']([^"\'>\s]+)["\']', unescaped)
    for title_cand, raw_link in title_matches:
        clean_cand = title_cand.strip(" -–—:•*[]()")
        clean_l = raw_link.rstrip(".,);]>'\"")
        if clean_cand and not clean_cand.startswith("http") and not clean_cand.lower().startswith("and more"):
            if "|" in clean_cand:
                parts_cand = [x.strip() for x in clean_cand.split("|") if x.strip()]
                clean_cand = parts_cand[-1] if parts_cand else clean_cand
            link_titles[clean_l] = clean_cand

    if links:
        for idx, link in enumerate(links):
            link_lower = link.lower()
            if "ashby" in link_lower:
                ats = "Ashby"
            elif "greenhouse" in link_lower:
                ats = "Greenhouse"
            elif "lever" in link_lower:
                ats = "Lever"
            elif "workable" in link_lower:
                ats = "Workable"
            elif "rippling" in link_lower:
                ats = "Rippling"
            elif "personio" in link_lower:
                ats = "Personio"
            elif "smartrecruiters" in link_lower:
                ats = "SmartRecruiters"
            elif "myworkdayjobs" in link_lower:
                ats = "Workday"
            else:
                ats = "Direct ATS"

            # Extract slug
            slug = ""
            m_slug = re.search(r'(?:jobs\.ashbyhq\.com|app\.ashbyhq\.com|boards\.greenhouse\.io|job-boards\.greenhouse\.io|jobs\.lever\.co|apply\.workable\.com|ats\.rippling\.com)/([^/?#]+)', link, re.I)
            if m_slug:
                slug = m_slug.group(1).lower()

            if base_company and len(base_company) <= 50 and not base_company.startswith("http"):
                company = base_company
            elif slug and slug not in ["jobs", "embed", "job_board", "j", "api"]:
                company = slug.replace("-", " ").replace("_", " ").title()
            else:
                # Do not fabricate "HN Startup"
                continue

            role_title = link_titles.get(link) or base_title or "Software Engineer"
            is_intern = bool(re.search(r'\b(intern|internship|co-op)\b', f"{role_title} {clean}", re.I))
            if base_location:
                loc = base_location
            elif is_remote_mentioned:
                loc = "Remote"
            else:
                loc = "On-site / Unspecified"

            job_id = generate_job_id(company, role_title, link, comment_id=comment_id)

            jobs.append(JobRequisition(
                id=job_id,
                company=company,
                title=role_title,
                location=loc,
                apply_url=link,
                description_text=clean,
                is_internship=is_intern,
                ats=ats,
                hn_permalink=hn_link
            ))
    else:
        # No ATS link found: Check for DIRECT_FOUNDER_EMAIL
        if not has_pipes and not RE_HIRING_INTENT.search(clean):
            return []

        emails = extract_founder_emails(clean)
        if emails:
            # Filter emails: ignore personal webmail unless a real company was parsed from the pipe header
            valid_emails = []
            for em in emails:
                domain = em.split("@")[-1].lower() if "@" in em else ""
                if domain in PERSONAL_WEBMAILS and not base_company:
                    continue
                valid_emails.append(em)

            if valid_emails:
                company = base_company
                if not company and not has_pipes:
                    m_hiring = re.search(r'\b([A-Z][a-zA-Z0-9_\-\.]{2,30})\s+(?:is|are)\s+hiring\b', clean)
                    if m_hiring:
                        company = m_hiring.group(1)

                if not company:
                    # Do not fabricate "HN Startup"
                    return []

                role_title = base_title
                if not role_title:
                    m_role = re.search(r'\b((?:software|backend|frontend|full\s*stack|systems?|infrastructure|devops|cloud|platform|ai|ml|data)\s+(?:engineer|developer|intern))\b', clean, re.I)
                    if m_role:
                        role_title = m_role.group(1).title()
                    else:
                        return []

                if base_location:
                    loc = base_location
                elif is_remote_mentioned:
                    loc = "Remote"
                else:
                    loc = "On-site / Unspecified"

                is_intern = bool(re.search(r'\b(intern|internship|co-op)\b', f"{role_title} {clean}", re.I))

                for email in valid_emails[:2]:
                    job_id = generate_job_id(company, role_title, f"mailto:{email}", comment_id=comment_id, email=email)
                    jobs.append(JobRequisition(
                        id=job_id,
                        company=company,
                        title=role_title,
                        location=loc,
                        apply_url=f"mailto:{email}",
                        description_text=clean,
                        is_internship=is_intern,
                        ats="DIRECT_FOUNDER_EMAIL",
                        contact_email=email,
                        hn_permalink=hn_link
                    ))

    return jobs

async def fetch_hn_who_is_hiring_jobs(client: httpx.AsyncClient) -> Tuple[List[JobRequisition], List[Dict[str, str]]]:
    """
    Fetches the latest official Hacker News 'Who is hiring?' thread and parses comments.
    Returns: (parsed_jobs, newly_discovered_companies)
    """
    try:
        search_res = await client.get(HN_SEARCH_URL, timeout=12.0)
        if search_res.status_code != 200:
            return [], []

        hits = search_res.json().get("hits", [])
        if not hits:
            return [], []

        # Find the latest top-level thread
        hiring_threads = [h for h in hits if "who is hiring" in h.get("title", "").lower()]
        if not hiring_threads:
            return [], []

        latest_thread = hiring_threads[0]
        item_id = latest_thread.get("objectID")

        item_url = HN_ITEM_URL.format(item_id=item_id)
        item_res = await client.get(item_url, timeout=15.0)
        if item_res.status_code != 200:
            return [], []

        story_data = item_res.json()
        children = story_data.get("children", [])

        all_jobs = []
        new_companies = []
        seen_slugs = set()

        for comment in children:
            comment_text = comment.get("text") or ""
            cid = str(comment.get("id", ""))
            if not comment_text:
                continue

            comment_jobs = parse_hn_comment(comment_text, comment_id=cid)
            all_jobs.extend(comment_jobs)

            # Discover new ATS slugs
            for cj in comment_jobs:
                if cj.ats not in ["DIRECT_FOUNDER_EMAIL", "Direct ATS"]:
                    slug_match = re.search(r'(?:jobs\.ashbyhq\.com|boards\.greenhouse\.io|jobs\.lever\.co|apply\.workable\.com|ats\.rippling\.com)/([^/?#]+)', cj.apply_url, re.I)
                    if slug_match:
                        slug = slug_match.group(1).lower()
                        if slug not in seen_slugs and slug not in ["jobs", "embed", "job_board", "j", "api"]:
                            seen_slugs.add(slug)
                            new_companies.append({
                                "name": cj.company,
                                "slug": slug,
                                "ats": cj.ats.lower(),
                                "discovered_from": "hn_who_is_hiring"
                            })

        return all_jobs, new_companies
    except Exception:
        return [], []

fetch_hn_feed = fetch_hn_who_is_hiring_jobs

