"""
PhD and academic position scrapers:
FindAPhD, EurAxess, PhDPortal, EMBL/EBI/Sanger,
Nature Careers, Science Careers, AcademicPositions, Google Scholar RSS.
"""

from __future__ import annotations
import time
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import requests

from filters.scorer import Listing
from scrapers.utils import (
    HEADERS, strip_html, extract_country, detect_experience_level,
    is_funded, is_phd_listing,
)

try:
    from bs4 import BeautifulSoup
    BS4 = True
except ImportError:
    BS4 = False


def scrape_findaphd(keywords: list[str], max_results: int = 40) -> list[Listing]:
    """FindAPhD — HTML scraper, world's largest PhD listing board."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    if not BS4:
        print("  [FindAPhD] Install beautifulsoup4: pip install beautifulsoup4 lxml")
        return []

    for kw in keywords[:3]:
        url = f"https://www.findaphd.com/phds/?Keywords={quote_plus(kw)}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select(".phd-result, .phd-result__item, [class*='result-item']"):
                try:
                    t_el = card.select_one("h3 a, h4 a, .phd-result__title a, h2 a")
                    if not t_el:
                        continue
                    title = t_el.get_text(strip=True)
                    href  = t_el.get("href", "")
                    link  = f"https://www.findaphd.com{href}" if href.startswith("/") else href

                    if link in seen:
                        continue
                    seen.add(link)

                    inst_el = card.select_one(".institution, .uni-link, [class*='institution']")
                    inst    = inst_el.get_text(strip=True) if inst_el else ""
                    loc_el  = card.select_one(".location, [class*='location']")
                    loc     = loc_el.get_text(strip=True) if loc_el else ""
                    desc_el = card.select_one("p, .phd-result__description, [class*='description']")
                    desc    = desc_el.get_text(strip=True) if desc_el else ""

                    combined = f"{title} {desc}".lower()

                    listings.append(Listing(
                        title            = title,
                        description      = desc,
                        institution      = inst,
                        location         = loc,
                        country          = extract_country(loc),
                        funded           = is_funded(combined),
                        experience_level = detect_experience_level(combined),
                        url              = link,
                        source           = "FindAPhD",
                        listing_type     = "phd",
                    ))
                except Exception:
                    continue
        except Exception as e:
            print(f"  [FindAPhD] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_euraxess(keywords: list[str], max_results: int = 40) -> list[Listing]:
    """EurAxess — official EU researcher portal via RSS."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    for kw in keywords[:3]:
        url = f"https://euraxess.ec.europa.eu/jobs/rss?keywords={quote_plus(kw)}"
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

                loc = ""
                for tag in entry.get("tags", []):
                    term = tag.get("term", "")
                    if extract_country(term):
                        loc = term
                        break

                combined = f"{title} {summary}".lower()

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = loc,
                    country          = extract_country(loc),
                    posted_date      = pub,
                    funded           = is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "EurAxess",
                    listing_type     = "phd" if is_phd_listing(combined) else "job",
                ))
        except Exception as e:
            print(f"  [EurAxess] '{kw}': {e}")
        time.sleep(0.8)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_phdportal(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """PhDPortal.eu — major EU PhD aggregator via HTML."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    if not BS4:
        print("  [PhDPortal] Install beautifulsoup4: pip install beautifulsoup4 lxml")
        return []

    for kw in keywords[:3]:
        url = f"https://www.phdportal.eu/search/?keywords={quote_plus(kw)}&degree=phd"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select(".ProgrammeItem, [class*='programme'], article"):
                try:
                    t_el = card.select_one("h3 a, h2 a, .ProgrammeItem-title a, [class*='title'] a")
                    if not t_el:
                        continue
                    title = t_el.get_text(strip=True)
                    href  = t_el.get("href", "")
                    link  = f"https://www.phdportal.eu{href}" if href.startswith("/") else href

                    if link in seen:
                        continue
                    seen.add(link)

                    inst_el = card.select_one("[class*='university'], [class*='institution']")
                    inst    = inst_el.get_text(strip=True) if inst_el else ""
                    loc_el  = card.select_one("[class*='country'], [class*='location']")
                    loc     = loc_el.get_text(strip=True) if loc_el else ""

                    listings.append(Listing(
                        title            = title,
                        institution      = inst,
                        location         = loc,
                        country          = extract_country(loc),
                        experience_level = "PhD",
                        url              = link,
                        source           = "PhDPortal.eu",
                        listing_type     = "phd",
                    ))
                except Exception:
                    continue
        except Exception as e:
            print(f"  [PhDPortal] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_embl(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """EMBL, EMBL-EBI, Wellcome Sanger Institute — top-tier institutes via RSS."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    feeds = [
        ("EMBL",   "https://www.embl.org/jobs/feed/",       "Germany"),
        ("EBI",    "https://www.ebi.ac.uk/about/jobs/rss",  "UK"),
        ("Sanger", "https://jobs.sanger.ac.uk/rss",         "UK"),
    ]
    kw_lower = [k.lower() for k in keywords]

    for short, feed_url, country in feeds:
        try:
            feed = feedparser.parse(feed_url)
            institute = {"EMBL": "EMBL", "EBI": "EMBL-EBI", "Sanger": "Wellcome Sanger Institute"}[short]

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
                    institution      = institute,
                    location         = country,
                    country          = country,
                    posted_date      = pub,
                    funded           = True,
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = f"EMBL/{short}",
                    listing_type     = "phd" if is_phd_listing(combined) else "job",
                ))
        except Exception as e:
            print(f"  [EMBL/{short}]: {e}")
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_nature_careers(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """Nature Careers and Science Careers via RSS."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    kw_lower = [k.lower() for k in keywords]

    feeds = [
        ("Nature Careers",  "https://www.nature.com/naturecareers/rss/current"),
        ("Science Careers", "https://jobs.sciencecareers.org/rss/jobs/"),
    ]

    for source, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
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

                loc = ""
                for tag in entry.get("tags", []):
                    term = tag.get("term", "")
                    if extract_country(term):
                        loc = term
                        break

                listings.append(Listing(
                    title            = title,
                    description      = summary,
                    location         = loc,
                    country          = extract_country(loc),
                    posted_date      = pub,
                    funded           = is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = source,
                    listing_type     = "phd" if is_phd_listing(combined) else "job",
                ))
        except Exception as e:
            print(f"  [{source}]: {e}")
        time.sleep(0.5)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_academic_positions(keywords: list[str], max_results: int = 30) -> list[Listing]:
    """AcademicPositions.com — EU university research and PhD positions via HTML."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    if not BS4:
        print("  [AcademicPositions] Install beautifulsoup4: pip install beautifulsoup4 lxml")
        return []

    for kw in keywords[:3]:
        url = f"https://academicpositions.com/jobs?q={quote_plus(kw)}&type=phd"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select("article, .job-item, [class*='position-item']"):
                try:
                    t_el = card.select_one("h2 a, h3 a, .job-title a, [class*='title'] a")
                    if not t_el:
                        continue
                    title = t_el.get_text(strip=True)
                    href  = t_el.get("href", "")
                    link  = f"https://academicpositions.com{href}" if href.startswith("/") else href

                    if link in seen:
                        continue
                    seen.add(link)

                    inst_el = card.select_one("[class*='employer'], [class*='university']")
                    inst    = inst_el.get_text(strip=True) if inst_el else ""
                    loc_el  = card.select_one("[class*='location'], [class*='country']")
                    loc     = loc_el.get_text(strip=True) if loc_el else ""

                    listings.append(Listing(
                        title            = title,
                        institution      = inst,
                        location         = loc,
                        country          = extract_country(loc),
                        experience_level = "PhD",
                        url              = link,
                        source           = "AcademicPositions",
                        listing_type     = "phd",
                    ))
                except Exception:
                    continue
        except Exception as e:
            print(f"  [AcademicPositions] '{kw}': {e}")
        time.sleep(1)
        if len(listings) >= max_results:
            break

    return listings[:max_results]


def scrape_scholar_rss(keywords: list[str], max_results: int = 20) -> list[Listing]:
    """Google Scholar Alerts via user-configured RSS feeds in config/scholar_rss_feeds.txt."""
    listings: list[Listing] = []
    seen:     set[str]       = set()

    feeds_file = Path("config/scholar_rss_feeds.txt")
    if not feeds_file.exists():
        return []

    feed_urls = [
        line.strip() for line in feeds_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not feed_urls:
        return []

    kw_lower = [k.lower() for k in keywords]

    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
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
                    posted_date      = pub,
                    funded           = is_funded(combined),
                    experience_level = detect_experience_level(combined),
                    url              = link,
                    source           = "Google Scholar",
                    listing_type     = "phd" if is_phd_listing(combined) else "job",
                ))
        except Exception as e:
            print(f"  [Scholar RSS]: {e}")
        if len(listings) >= max_results:
            break

    return listings[:max_results]
