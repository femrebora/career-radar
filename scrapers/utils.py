"""Shared helpers used by all scrapers."""

from __future__ import annotations
import html
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_HTML_RE     = re.compile(r"<[^>]+>")
_SPACES_RE   = re.compile(r"\s+")

def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = _HTML_RE.sub(" ", text)
    return _SPACES_RE.sub(" ", text).strip()


_SALARY_RE = re.compile(
    r"[\$£€]\s?[\d,]+(?:\s?[-–]\s?[\$£€]?\s?[\d,]+)?(?:\s?[kK])?"
    r"(?:\s?(?:per|/|p\.a\.?|year|yr|month|annual))?",
    re.IGNORECASE,
)

def extract_salary(text: str) -> str:
    m = _SALARY_RE.search(text or "")
    return m.group(0).strip() if m else ""


_COUNTRY_MAP: dict[str, str] = {
    "germany": "Germany", "deutschland": "Germany",
    "united kingdom": "UK", "uk": "UK", "great britain": "UK",
    "england": "UK", "scotland": "UK", "wales": "UK",
    "united states": "USA", "usa": "USA", "u.s.a": "USA",
    "netherlands": "Netherlands", "holland": "Netherlands",
    "france": "France", "spain": "Spain", "italy": "Italy",
    "switzerland": "Switzerland", "austria": "Austria",
    "sweden": "Sweden", "denmark": "Denmark", "norway": "Norway",
    "finland": "Finland", "belgium": "Belgium", "portugal": "Portugal",
    "canada": "Canada", "australia": "Australia", "new zealand": "New Zealand",
    "china": "China", "japan": "Japan", "singapore": "Singapore",
    "remote": "Remote", "worldwide": "Remote", "global": "Remote",
    "europe": "Europe", "eu": "Europe",
}

def extract_country(text: str) -> str:
    t = (text or "").lower()
    for key, name in _COUNTRY_MAP.items():
        if key in t:
            return name
    return ""


_FUNDED_RE = re.compile(
    r"\b(fully[\s-]?funded|stipend|scholarship|fellowship|funded|financing|grant|bursary)\b",
    re.IGNORECASE,
)

def is_funded(text: str) -> bool:
    return bool(_FUNDED_RE.search(text or ""))


_PHD_RE = re.compile(
    r"\b(ph\.?d\.?|doctoral|phd position|phd student|doctorate|thesis|dissertation)\b",
    re.IGNORECASE,
)

def is_phd_listing(text: str) -> bool:
    return bool(_PHD_RE.search(text or ""))


_EXPERIENCE_RULES = [
    (re.compile(r"\b(professor|faculty|principal investigator|senior lecturer|associate professor)\b", re.I), "Senior"),
    (re.compile(r"\b(postdoc|post-doc|post doc|research fellow|staff scientist|senior scientist|senior researcher)\b", re.I), "Postdoc"),
    (re.compile(r"\b(ph\.?d\.?|doctoral|phd student|phd candidate)\b", re.I), "PhD"),
    (re.compile(r"\b(junior|entry.?level|graduate|intern|internship|trainee|early.?career)\b", re.I), "Entry"),
    (re.compile(r"\b(mid.?level|intermediate|[345]\+\s?years?)\b", re.I), "Mid"),
]

def detect_experience_level(text: str) -> str:
    for pattern, level in _EXPERIENCE_RULES:
        if pattern.search(text or ""):
            return level
    return ""
