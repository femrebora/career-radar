"""
Additional scrapers — platforms not in jobs.py or phd.py.

Sources added here:
  Job boards:
    Jobicy          — remote jobs JSON API (free, no key)
    HigherEdJobs    — US academic / research jobs RSS
    The Muse        — company culture + jobs JSON API (free)
    GitHub Jobs     — tech jobs via GitHub (archived but mirrors exist)
    Jobspresso      — remote jobs RSS

  PhD / Academic:
    Times Higher Education (THE) Jobs — top global academic jobs RSS
    HigherEdJobs    — US university research / faculty RSS
    ResearchGate    — job search URL builder (scraping blocked, login required)
    JSTOR Global Plants / Jobs — niche academic RSS
    jobs.ac.uk      — UK academic jobs (largest in UK)
    DAAD             — German academic funding / PhD positions
    Marie Curie / MSCA — EU fellowship programme listings
"""

from __future__ import annotations
import time
import requests
import feedparser
from urllib.parse import quote_plus, urlencode

from filters.scorer import Listing
from scrapers.utils import (
    HEADERS, strip_html, extract_salary, extract_country,
    detect_experience_level, is_funded, is_phd_listing,
)


# ── Jobicy (JSON API, remote jobs) ─────────────────────────────────────────────

def scrape_jobicy(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """
    Scrape Jobicy.com — free public JSON API, no key needed.
    Best for remote tech / data / research roles at global companies.
    Docs: https://jobicy.com/jobs-rss-feed
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:4]:
        url = f"https://jobicy.com/api/v2/remote-jobs?tag={quote_plus(kw)}&count=20"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()
            jobs = data.get("jobs", [])

            for job in jobs:
                title   = job.get("jobTitle", "")
                company = job.get("companyName", "")
                loc     = job.get("jobGeo", "Worldwide")
                desc    = strip_html(job.get("jobDescription", ""))
                link    = job.get("url", "")
                date    = job.get("pubDate", "")
                salary  = job.get("annualSalaryMin", "")
                sal_max = job.get("annualSalaryMax", "")
                if salary and sal_max:
                    salary = f"${salary}–${sal_max}"
                elif salary:
                    salary = f"from ${salary}"

                if link in seen:
                    continue
                seen.add(link)

                listings.append(Listing(
                    title            = title,
                    description      = desc,
                    company          = company,
                    location         = loc,
                    country          = extract_country(loc) or "Remote",
                    posted_date      = date,
                    salary           = str(salary),
                    job_type         = "remote",
                    experience_level = detect_experience_level(f"{title} {desc}"),
                    url              = link,
                    source           = "Jobicy",
                    listing_type     = "job",
                ))
        except Exception as e:
            print(f"  [Jobicy] '{kw}': {e}")
        time.sleep(0.8)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── jobs.ac.uk (UK academic jobs RSS) ─────────────────────────────────────────

def scrape_jobsacuk(keywords: list[str], max_results: int = 40) -> list[Listing]:
    """
    Scrape jobs.ac.uk — the largest UK academic job board.
    Covers PhD studentships, research fellowships, postdocs, lectureships.
    RSS feed supports keyword filtering.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:4]:
        rss_url = f"https://www.jobs.ac.uk/search/?keywords={quote_plus(kw)}&type=rss"
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries:
                title   = entry.get("title", "")
                link    = entry.get("link", "")
                summary = strip_html(entry.get("summary", ""))
                pub     = entry.get("published", "")

                if link in seen:
                    continue
                seen.add(link)

                combined = f"{title} {summary}".lower()
                is_phd_  = is_phd_listing(combined)

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = "UK",
                    country          = "UK",
                    posted_date      = pub,
                    funded           = is_phd_ and is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "jobs.ac.uk",
                    listing_type     = "phd" if is_phd_ else "job",
                ))
        except Exception as e:
            print(f"  [jobs.ac.uk] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── Times Higher Education Jobs ────────────────────────────────────────────────

def scrape_the_jobs(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """
    Scrape Times Higher Education (THE) Jobs — global academic positions.
    Strong for senior academic, research fellow, and international faculty roles.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:3]:
        # THE jobs search RSS
        url = f"https://www.timeshighereducation.com/unijobs/listings/?q={quote_plus(kw)}&format=rss"
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

                # Extract location from tags
                loc = ""
                for tag in entry.get("tags", []):
                    term = tag.get("term", "")
                    if extract_country(term):
                        loc = term
                        break

                combined = f"{title} {summary}".lower()
                is_phd_  = is_phd_listing(combined)

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = loc,
                    country          = extract_country(loc),
                    posted_date      = pub,
                    funded           = is_phd_ and is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "Times Higher Ed",
                    listing_type     = "phd" if is_phd_ else "job",
                ))
        except Exception as e:
            print(f"  [THE Jobs] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── HigherEdJobs (US academic) ─────────────────────────────────────────────────

def scrape_higheredjobs(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """
    Scrape HigherEdJobs.com — largest US academic/higher education job board.
    Strong for US university research positions, postdocs, faculty.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:3]:
        url = f"https://www.higheredjobs.com/rss/articleFeed.cfm?JobCat=211&Keyword={quote_plus(kw)}"
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

                combined = f"{title} {summary}".lower()
                is_phd_  = is_phd_listing(combined)

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = "USA",
                    country          = "USA",
                    posted_date      = pub,
                    funded           = is_phd_ and is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "HigherEdJobs",
                    listing_type     = "phd" if is_phd_ else "job",
                ))
        except Exception as e:
            print(f"  [HigherEdJobs] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── DAAD (German Academic Exchange / PhD funding) ─────────────────────────────

def scrape_daad(keywords: list[str], max_results: int = 20) -> list[Listing]:
    """
    Scrape DAAD scholarship/position database.
    DAAD (Deutscher Akademischer Austauschdienst) is the main German academic
    funding body — excellent for funded PhD and postdoc positions in Germany.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:3]:
        url = (
            f"https://www.daad.de/en/studying-in-germany/scholarships/"
            f"daad-scholarship-database/?type=dt&subjectGrpId=&daad=1&q={quote_plus(kw)}&page=1"
        )
        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select(".c-result-item, .scholarship-item, article"):
                try:
                    t_el = card.select_one("h3 a, h2 a, .c-result-item__title a")
                    if not t_el:
                        continue
                    title = t_el.get_text(strip=True)
                    href  = t_el.get("href", "")
                    link  = f"https://www.daad.de{href}" if href.startswith("/") else href

                    if link in seen:
                        continue
                    seen.add(link)

                    desc_el = card.select_one("p, .description, .c-result-item__description")
                    desc    = desc_el.get_text(strip=True) if desc_el else ""
                    dl_el   = card.select_one(".deadline, .c-result-item__deadline")
                    deadline= dl_el.get_text(strip=True) if dl_el else ""

                    listings.append(Listing(
                        title        = title,
                        description  = desc,
                        institution  = "DAAD",
                        location     = "Germany",
                        country      = "Germany",
                        deadline     = deadline,
                        funded       = True,    # DAAD listings are always funding opportunities
                        url          = link,
                        source       = "DAAD",
                        listing_type = "phd",
                    ))
                except Exception:
                    continue
        except Exception as e:
            print(f"  [DAAD] '{kw}': {e}")
        time.sleep(1.5)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── Marie Skłodowska-Curie Actions (MSCA) ─────────────────────────────────────

def scrape_msca(keywords: list[str], max_results: int = 20) -> list[Listing]:
    """
    Scrape MSCA (Marie Curie) fellowship listings via the EURAXESS search
    (MSCA fellowships are posted on EurAxess and the EU Funding Portal).
    These are among the most prestigious fully-funded PhD/postdoc positions in Europe.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    rss_url = "https://euraxess.ec.europa.eu/jobs/rss?type=msca"
    try:
        feed = feedparser.parse(rss_url)
        kw_lower = [k.lower() for k in keywords]

        for entry in feed.entries:
            title   = entry.get("title", "")
            link    = entry.get("link", "")
            summary = entry.get("summary", "")
            pub     = entry.get("published", "")

            combined = f"{title} {summary}".lower()
            if not any(k in combined for k in kw_lower):
                continue

            if link in seen:
                continue
            seen.add(link)

            loc = ""
            for tag in entry.get("tags", []):
                term = tag.get("term", "")
                if extract_country(term):
                    loc = term
                    break

            combined_lower = combined
            is_phd_ = is_phd_listing(combined_lower) or "fellow" in combined_lower

            listings.append(Listing(
                title            = title,
                description      = strip_html(summary),
                institution      = "Marie Curie / MSCA",
                location         = loc,
                country          = extract_country(loc),
                posted_date      = pub,
                funded           = True,    # MSCA fellowships are always fully funded
                experience_level = "Postdoc" if "postdoc" in combined_lower else "Entry",
                url              = link,
                source           = "MSCA (Marie Curie)",
                listing_type     = "phd" if is_phd_ else "job",
            ))
    except Exception as e:
        print(f"  [MSCA] RSS: {e}")

    return listings[:max_results]


# ── The Muse (JSON API, company culture + jobs) ────────────────────────────────

def scrape_the_muse(keywords: list[str], max_results: int = 20) -> list[Listing]:
    """
    Scrape The Muse via their free public API.
    Best for tech/data/science roles at companies with strong culture pages.
    API docs: https://www.themuse.com/developers/api/v2
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    for kw in keywords[:3]:
        url = f"https://www.themuse.com/api/public/jobs?category={quote_plus(kw)}&page=1&descending=true"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            data = resp.json()
            jobs = data.get("results", [])

            for job in jobs[:15]:
                title   = job.get("name", "")
                company = job.get("company", {}).get("name", "")
                link    = job.get("refs", {}).get("landing_page", "")
                pub     = job.get("publication_date", "")
                desc    = " ".join(
                    c.get("body", "") for c in job.get("contents", [])
                    if isinstance(c, dict)
                )
                desc    = strip_html(desc)

                # Location
                locs    = job.get("locations", [])
                loc     = locs[0].get("name", "") if locs else ""
                country = extract_country(loc)

                if link in seen:
                    continue
                seen.add(link)

                listings.append(Listing(
                    title            = title,
                    description      = desc,
                    company          = company,
                    location         = loc,
                    country          = country,
                    posted_date      = pub,
                    experience_level = detect_experience_level(f"{title} {desc}"),
                    url              = link,
                    source           = "The Muse",
                    listing_type     = "job",
                ))
        except Exception as e:
            print(f"  [The Muse] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


# ── Jobspresso (remote jobs RSS) ──────────────────────────────────────────────

def scrape_jobspresso(keywords: list[str], max_results: int = 20) -> list[Listing]:
    """
    Scrape Jobspresso.co — curated remote job board.
    Best for tech, marketing, design, and data science remote roles.
    """
    listings: list[Listing] = []
    seen: set[str] = set()

    rss_url = "https://jobspresso.co/feed/"
    kw_lower = [k.lower() for k in keywords]

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
                source           = "Jobspresso",
                listing_type     = "job",
            ))
    except Exception as e:
        print(f"  [Jobspresso] RSS: {e}")

    return listings[:max_results]


# ── ResearchGate & Academia.edu — URL builders only ───────────────────────────

def get_researchgate_urls(keywords: list[str]) -> list[str]:
    """
    ResearchGate blocks scraping and requires login for full access.
    Returns search URLs to open manually.
    """
    base = "https://www.researchgate.net/jobs/search"
    return [
        f"{base}?keywords={quote_plus(kw)}"
        for kw in keywords[:4]
    ]


def get_h1bdata_urls(keywords: list[str]) -> list[str]:
    """
    H1BGrader / myvisajobs — useful for finding US employers who sponsor visas
    for bioinformatics/research roles. URL builder only.
    """
    base = "https://www.myvisajobs.com/Search_Visa_Sponsoring_Employer.aspx"
    return [
        f"{base}?T={quote_plus(kw)}"
        for kw in keywords[:3]
    ]
