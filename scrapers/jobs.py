"""
Job board scrapers: Indeed, Adzuna, RemoteOK, Arbeitnow, WeWorkRemotely.
Also URL builders for LinkedIn and Glassdoor (scraping blocked on both).
"""

from __future__ import annotations
import time

import feedparser
import requests
from urllib.parse import quote_plus, urlencode

from filters.scorer import Listing
from scrapers.utils import (
    HEADERS, strip_html, extract_salary, extract_country,
    detect_experience_level,
)


def scrape_indeed(keywords: list[str], roles: list[str], max_results: int = 40) -> list[Listing]:
    """Indeed RSS — USA, UK, Germany."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    query_terms = (roles[:2] + keywords[:2]) if roles else keywords[:3]

    country_feeds = [
        ("USA", "https://www.indeed.com/rss"),
        ("UK",  "https://www.indeed.co.uk/rss"),
        ("Germany", "https://de.indeed.com/rss"),
    ]

    for country_label, base_url in country_feeds:
        for kw in query_terms[:2]:
            url = f"{base_url}?q={quote_plus(kw)}&sort=date"
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    title   = entry.get("title", "")
                    link    = entry.get("link", "")
                    summary = strip_html(entry.get("summary", ""))
                    pub     = entry.get("published", "")

                    if link in seen:
                        continue
                    seen.add(link)

                    listings.append(Listing(
                        title            = title,
                        description      = summary,
                        location         = country_label,
                        country          = country_label,
                        posted_date      = pub,
                        salary           = extract_salary(summary),
                        experience_level = detect_experience_level(f"{title} {summary}"),
                        url              = link,
                        source           = "Indeed",
                        listing_type     = "job",
                    ))
            except Exception as e:
                print(f"  [Indeed/{country_label}] '{kw}': {e}")
            time.sleep(0.5)
            if len(listings) >= max_results:
                return listings[:max_results]

    return listings[:max_results]


def scrape_adzuna(keywords: list[str], country_code: str = "gb", max_results: int = 30) -> list[Listing]:
    """Adzuna RSS — multi-country."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    _domains = {
        "gb": ("www.adzuna.co.uk", "UK"),
        "us": ("www.adzuna.com",   "USA"),
        "de": ("www.adzuna.de",    "Germany"),
        "au": ("www.adzuna.com.au","Australia"),
        "ca": ("www.adzuna.ca",    "Canada"),
        "fr": ("www.adzuna.fr",    "France"),
        "nl": ("www.adzuna.nl",    "Netherlands"),
    }
    domain, country_label = _domains.get(country_code, ("www.adzuna.co.uk", "UK"))

    for kw in keywords[:3]:
        url = f"https://{domain}/jobs/rss?q={quote_plus(kw)}"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title   = entry.get("title", "")
                link    = entry.get("link", "")
                summary = strip_html(entry.get("summary", ""))
                pub     = entry.get("published", "")

                if link in seen:
                    continue
                seen.add(link)

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = country_label,
                    country          = country_label,
                    posted_date      = pub,
                    salary           = extract_salary(summary),
                    experience_level = detect_experience_level(f"{title} {summary}"),
                    url              = link,
                    source           = "Adzuna",
                    listing_type     = "job",
                ))
        except Exception as e:
            print(f"  [Adzuna/{country_code}] '{kw}': {e}")
        time.sleep(0.5)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_remoteok(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """RemoteOK JSON API — free, no key required."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        jobs = resp.json()
        # First item is a legal notice dict, not a job
        if isinstance(jobs, list) and jobs and isinstance(jobs[0], dict) and "legal" in jobs[0]:
            jobs = jobs[1:]

        kw_lower = [k.lower() for k in keywords]
        for job in jobs:
            if not isinstance(job, dict):
                continue
            title   = job.get("position", "")
            company = job.get("company", "")
            tags    = " ".join(job.get("tags", []))
            desc    = strip_html(job.get("description", ""))
            link    = job.get("url", "")
            pub     = job.get("date", "")
            salary  = job.get("salary", "")

            combined = f"{title} {company} {tags} {desc}".lower()
            if not any(k in combined for k in kw_lower):
                continue
            if link in seen:
                continue
            seen.add(link)

            listings.append(Listing(
                title            = title,
                description      = desc,
                company          = company,
                location         = "Remote",
                country          = "Remote",
                posted_date      = pub,
                salary           = str(salary) if salary else "",
                job_type         = "remote",
                experience_level = detect_experience_level(f"{title} {desc}"),
                url              = link,
                source           = "RemoteOK",
                listing_type     = "job",
            ))
            if len(listings) >= max_results:
                break
    except Exception as e:
        print(f"  [RemoteOK]: {e}")

    return listings[:max_results]


def scrape_arbeitnow(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """Arbeitnow JSON API — Europe-focused, no key required."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    for kw in keywords[:3]:
        url = f"https://www.arbeitnow.com/api/job-board-api?search={quote_plus(kw)}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            jobs = resp.json().get("data", [])

            for job in jobs:
                title   = job.get("title", "")
                company = job.get("company_name", "")
                loc     = job.get("location", "")
                desc    = strip_html(job.get("description", ""))
                link    = job.get("url", "")
                pub     = str(job.get("created_at", ""))
                remote  = job.get("remote", False)

                if link in seen:
                    continue
                seen.add(link)

                listings.append(Listing(
                    title            = title,
                    description      = desc,
                    company          = company,
                    location         = loc,
                    country          = extract_country(loc) or "Europe",
                    posted_date      = pub,
                    job_type         = "remote" if remote else "",
                    experience_level = detect_experience_level(f"{title} {desc}"),
                    url              = link,
                    source           = "Arbeitnow",
                    listing_type     = "job",
                ))
        except Exception as e:
            print(f"  [Arbeitnow] '{kw}': {e}")
        time.sleep(0.5)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_weworkremotely(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """WeWorkRemotely RSS — curated remote roles."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    rss_feeds = [
        "https://weworkremotely.com/remote-jobs.rss",
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
    ]
    kw_lower = [k.lower() for k in keywords]

    for rss_url in rss_feeds:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title   = entry.get("title", "")
                link    = entry.get("link", "")
                summary = strip_html(entry.get("summary", ""))
                pub     = entry.get("published", "")

                combined = f"{title} {summary}".lower()
                if not any(k in combined for k in kw_lower):
                    continue
                if link in seen:
                    continue
                seen.add(link)

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = "Remote",
                    country          = "Remote",
                    posted_date      = pub,
                    job_type         = "remote",
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "WeWorkRemotely",
                    listing_type     = "job",
                ))
        except Exception as e:
            print(f"  [WeWorkRemotely]: {e}")
        time.sleep(0.3)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def get_linkedin_urls(keywords: list[str], roles: list[str]) -> list[str]:
    """Returns LinkedIn search URLs to open manually (scraping blocked)."""
    terms = roles[:3] if roles else keywords[:3]
    return [
        "https://www.linkedin.com/jobs/search/?" + urlencode({"keywords": t, "f_TPR": "r604800"})
        for t in terms
    ]


def get_glassdoor_urls(keywords: list[str]) -> list[str]:
    """Returns Glassdoor search URLs to open manually (scraping blocked)."""
    return [
        f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(kw)}"
        for kw in keywords[:3]
    ]
