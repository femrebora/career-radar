"""
phdscanner.com scraper — Playwright (headless Chromium)
========================================================
PhDScanner is a React SPA with no public API or RSS feed.
This scraper uses two strategies:

  Strategy A (preferred): API interception
    Playwright loads the page, intercepts the XHR/fetch calls the React app
    makes to its backend, and extracts the raw JSON — much faster than DOM parsing.

  Strategy B (fallback): DOM scraping
    If no JSON API is found, wait for React to render and parse the DOM.

Requirements:
    pip install playwright
    playwright install chromium

Usage from main.py:
    from scrapers.phdscanner import scrape_phdscanner
    listings = scrape_phdscanner(keywords=["bioinformatics", "cancer genomics"])
"""

from __future__ import annotations
import asyncio
import json
import time
from typing import Any

from filters.scorer import Listing
from scrapers.utils import extract_country, is_funded, detect_experience_level

# ── Constants ──────────────────────────────────────────────────────────────────

BASE_URL     = "https://www.phdscanner.com"
SEARCH_URL   = f"{BASE_URL}/phd-vacancies/standard/"
TIMEOUT_MS   = 30_000   # 30 s page load timeout
WAIT_AFTER_S = 4        # seconds to wait for React hydration

# CSS selectors — update these if phdscanner redesigns their UI
CARD_SELECTORS = [
    "[class*='vacancy']",
    "[class*='position']",
    "[class*='phd-card']",
    "[class*='job-card']",
    "article",
    ".card",
    "[data-testid*='vacancy']",
    "[data-testid*='position']",
]

TITLE_SELECTORS  = ["h2", "h3", "h4", "[class*='title']", "[class*='heading']"]
DESC_SELECTORS   = ["p", "[class*='desc']", "[class*='summary']", "[class*='abstract']"]
INST_SELECTORS   = ["[class*='university']", "[class*='institution']", "[class*='employer']"]
LOC_SELECTORS    = ["[class*='location']", "[class*='country']", "[class*='city']"]
LINK_SELECTORS   = ["a[href*='/phd']", "a[href*='/vacancy']", "a[href*='/position']", "a"]


# ── Async core ─────────────────────────────────────────────────────────────────

async def _scrape_async(
    keywords: list[str],
    max_results: int,
) -> list[Listing]:
    """
    Main async scraper. Tries API interception first, falls back to DOM.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("  [PhDScanner] playwright not installed.")
        print("  [PhDScanner] Run: pip install playwright && playwright install chromium")
        return []

    listings: list[Listing] = []
    intercepted_api: dict[str, Any] = {}   # url → json body

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

        # ── Stealth: hide webdriver flag ───────────────────────────────────────
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = await context.new_page()

        # ── Strategy A: intercept JSON API responses ───────────────────────────
        async def on_response(response):
            url = response.url
            ct  = response.headers.get("content-type", "")
            if "json" in ct and response.status == 200:
                # Capture any JSON response from the site's own domain
                if BASE_URL.replace("https://www.", "") in url or "phdscanner" in url:
                    try:
                        body = await response.json()
                        intercepted_api[url] = body
                    except Exception:
                        pass

        page.on("response", on_response)

        # ── Load search page ───────────────────────────────────────────────────
        try:
            await page.goto(SEARCH_URL, wait_until="networkidle", timeout=TIMEOUT_MS)
        except Exception:
            try:
                await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            except Exception as e:
                print(f"  [PhDScanner] Page load failed: {e}")
                await browser.close()
                return []

        await asyncio.sleep(WAIT_AFTER_S)

        # ── Try keyword search if there's a search box ─────────────────────────
        for keyword in keywords[:2]:
            try:
                search_box = await page.query_selector(
                    "input[type='search'], input[placeholder*='search' i], "
                    "input[placeholder*='keyword' i], input[name='q'], input[name='search']"
                )
                if search_box:
                    await search_box.fill(keyword)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(3)
            except Exception:
                pass

        # ── Strategy A: parse intercepted JSON ─────────────────────────────────
        if intercepted_api:
            print(f"  [PhDScanner] Intercepted {len(intercepted_api)} API calls → parsing JSON")
            for url, body in intercepted_api.items():
                listings.extend(_parse_api_response(body))
                if len(listings) >= max_results:
                    break

        # ── Strategy B: DOM scraping fallback ──────────────────────────────────
        if not listings:
            print("  [PhDScanner] No API intercepted → falling back to DOM scraping")
            listings = await _scrape_dom(page, max_results)

        # ── Pagination: try to click "Next" up to 3 times ─────────────────────
        page_count = 0
        while len(listings) < max_results and page_count < 3:
            try:
                next_btn = await page.query_selector(
                    "button:has-text('Next'), a:has-text('Next'), "
                    "[aria-label*='next' i], [class*='next']"
                )
                if not next_btn:
                    break
                await next_btn.click()
                await asyncio.sleep(3)
                new = await _scrape_dom(page, max_results - len(listings))
                if not new:
                    break
                listings.extend(new)
                page_count += 1
            except Exception:
                break

        await browser.close()

    return listings[:max_results]


def _parse_api_response(body: Any) -> list[Listing]:
    """
    Parse a JSON API response body into Listing objects.
    Handles various common response shapes: list, {data: [...]}, {results: [...]}, etc.
    """
    listings: list[Listing] = []

    # Unwrap common envelope patterns
    if isinstance(body, dict):
        for key in ("data", "results", "positions", "vacancies", "jobs", "items"):
            if key in body and isinstance(body[key], list):
                body = body[key]
                break
        else:
            # Single object — wrap it
            body = [body]

    if not isinstance(body, list):
        return []

    for item in body:
        if not isinstance(item, dict):
            continue

        title = (
            item.get("title") or item.get("position") or
            item.get("name") or item.get("job_title") or ""
        )
        if not title:
            continue

        desc = (
            item.get("description") or item.get("summary") or
            item.get("abstract") or item.get("body") or ""
        )
        inst = (
            item.get("university") or item.get("institution") or
            item.get("employer") or item.get("organization") or ""
        )
        dept  = item.get("department") or item.get("faculty") or ""
        loc   = item.get("location") or item.get("city") or item.get("country") or ""
        country = item.get("country") or extract_country(loc)
        deadline= item.get("deadline") or item.get("closing_date") or item.get("apply_by") or ""
        url   = item.get("url") or item.get("link") or item.get("href") or ""
        if url and not url.startswith("http"):
            url = f"{BASE_URL}{url}"

        funded_ = (
            item.get("funded") is True or
            item.get("funding") not in (None, "", "unfunded") or
            is_funded(f"{title} {desc}")
        )

        listings.append(Listing(
            title            = str(title),
            description      = str(desc),
            institution      = str(inst),
            department       = str(dept),
            location         = str(loc),
            country          = str(country),
            deadline         = str(deadline),
            funded           = funded_,
            experience_level = detect_experience_level(f"{title} {desc}"),
            url              = str(url),
            source           = "PhDScanner",
            listing_type     = "phd",
        ))

    return listings


async def _scrape_dom(page: Any, max_results: int) -> list[Listing]:
    """Fallback DOM scraper — used when no API is intercepted."""
    listings: list[Listing] = []
    seen: set[str] = set()

    # Try each card selector until we find matching elements
    cards = []
    for selector in CARD_SELECTORS:
        try:
            cards = await page.query_selector_all(selector)
            if len(cards) > 2:   # need at least a few to be meaningful
                break
        except Exception:
            continue

    if not cards:
        # Last resort: grab all text from the page
        try:
            text = await page.inner_text("body")
            print(f"  [PhDScanner] DOM: no cards found. Page text length: {len(text)}")
        except Exception:
            pass
        return []

    for card in cards[:max_results * 2]:
        try:
            # Title
            title = ""
            for sel in TITLE_SELECTORS:
                el = await card.query_selector(sel)
                if el:
                    title = (await el.inner_text()).strip()
                    if title:
                        break
            if not title:
                continue

            # URL
            url = ""
            for sel in LINK_SELECTORS:
                el = await card.query_selector(sel)
                if el:
                    href = await el.get_attribute("href")
                    if href:
                        url = href if href.startswith("http") else f"{BASE_URL}{href}"
                        break

            if url in seen:
                continue
            seen.add(url or title)

            # Description
            desc = ""
            for sel in DESC_SELECTORS:
                el = await card.query_selector(sel)
                if el:
                    desc = (await el.inner_text()).strip()
                    if desc:
                        break

            # Institution
            inst = ""
            for sel in INST_SELECTORS:
                el = await card.query_selector(sel)
                if el:
                    inst = (await el.inner_text()).strip()
                    if inst:
                        break

            # Location
            loc = ""
            for sel in LOC_SELECTORS:
                el = await card.query_selector(sel)
                if el:
                    loc = (await el.inner_text()).strip()
                    if loc:
                        break

            full_text = await card.inner_text()
            country   = extract_country(loc or full_text)
            funded_   = is_funded(full_text)

            listings.append(Listing(
                title            = title,
                description      = desc,
                institution      = inst,
                location         = loc,
                country          = country,
                funded           = funded_,
                experience_level = detect_experience_level(f"{title} {desc}"),
                url              = url,
                source           = "PhDScanner",
                listing_type     = "phd",
            ))

        except Exception:
            continue

    return listings[:max_results]


# ── Public sync wrapper ────────────────────────────────────────────────────────

def scrape_phdscanner(
    keywords: list[str],
    max_results: int = 50,
) -> list[Listing]:
    """
    Synchronous entry point called by main.py.

    Requires:
        pip install playwright
        playwright install chromium

    Falls back gracefully if Playwright isn't installed.
    """
    try:
        return asyncio.run(_scrape_async(keywords, max_results))
    except Exception as e:
        print(f"  [PhDScanner] Scraper error: {e}")
        return []
