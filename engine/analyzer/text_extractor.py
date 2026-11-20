import html
import re

TAG_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')

def clean_text(raw_html_or_text: str) -> str:
    """
    Cleans and normalizes job description text:
    - Decodes HTML entities (e.g. &lt;p&gt; -> <p>)
    - Strips all HTML tags
    - Normalizes consecutive whitespace and line breaks
    """
    if not raw_html_or_text:
        return ""
    # Decode twice in case of double-escaped entities like &amp;lt;
    text = html.unescape(raw_html_or_text)
    text = html.unescape(text)
    # Strip HTML tags
    text = TAG_RE.sub(" ", text)
    # Normalize whitespace
    return WHITESPACE_RE.sub(" ", text).strip()
