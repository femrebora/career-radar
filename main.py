#!/usr/bin/env python3
"""
career-radar — CLI tool to search job listings and funded PhD positions
across multiple platforms, filtered by a personal keyword profile.

Configure your search in: config/search_profile.yaml

Modes:
  --mode all   PhD positions + job listings  (default)
  --mode phd   PhD positions only
  --mode job   Job listings only

All sources
  Job boards  : indeed  adzuna  remoteok  arbeitnow  weworkremotely
                jobicy  themuse  jobspresso
  PhD boards  : findaphd  euraxess  phdportal  embl  nature
                academicpositions  scholar  phdscanner
                jobsacuk  the_jobs  higheredjobs  daad  msca

Usage:
  python main.py
  python main.py --mode phd
  python main.py --mode job --sources indeed remoteok arbeitnow jobicy
  python main.py --sources phdscanner findaphd euraxess
  python main.py --verbose
  python main.py --linkedin --glassdoor --researchgate
  python main.py --limit 60 --no-save
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml

try:
    from rich.console import Console
    console = Console()
    RICH = True
except ImportError:
    console = None
    RICH = False

from filters.scorer import RelevanceScorer, Listing
from filters.output import print_results_table, print_verbose, save_csv, save_markdown

# ── Source registry ────────────────────────────────────────────────────────────
JOB_SOURCES = [
    "indeed", "adzuna", "remoteok", "arbeitnow",
    "weworkremotely", "jobicy", "themuse", "jobspresso",
]
PHD_SOURCES = [
    "findaphd", "euraxess", "phdportal", "embl", "nature",
    "academicpositions", "scholar",
    "phdscanner",          # Playwright required
    "jobsacuk",            # UK academic
    "the_jobs",            # Times Higher Education
    "higheredjobs",        # US academic
    "daad",                # Germany / funded
    "msca",                # Marie Curie fellowships
]
ALL_SOURCES = JOB_SOURCES + PHD_SOURCES


def load_config(path: str = "config/search_profile.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run(label: str, func, *args, **kwargs) -> list[Listing]:
    if RICH:
        console.print(f"  [cyan]→[/cyan] [bold]{label}[/bold]...", end=" ")
    else:
        print(f"  → {label}...", end=" ", flush=True)
    try:
        t0 = time.time()
        results = func(*args, **kwargs)
        elapsed = time.time() - t0
        n = len(results)
        if RICH:
            console.print(f"[green]{n}[/green] [dim]({elapsed:.1f}s)[/dim]")
        else:
            print(f"{n} ({elapsed:.1f}s)")
        return results
    except Exception as e:
        if RICH:
            console.print(f"[red]error: {e}[/red]")
        else:
            print(f"error: {e}")
        return []


def print_urls(label: str, urls: list[str]) -> None:
    header = f"\n  [bold]{label}[/bold] — open in browser:"
    if RICH:
        console.print(header)
    else:
        print(header.replace("[bold]", "").replace("[/bold]", ""))
    for u in urls:
        if RICH:
            console.print(f"    [dim]→[/dim] {u}")
        else:
            print(f"  → {u}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="career-radar",
        description="Search job listings and PhD positions filtered by your keyword profile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Job sources:  " + "  ".join(JOB_SOURCES) + "\n"
            "PhD sources:  " + "  ".join(PHD_SOURCES)
        )
    )
    parser.add_argument("--mode", choices=["all", "phd", "job"], default="all")
    parser.add_argument("--sources", nargs="+", choices=ALL_SOURCES, metavar="SOURCE")
    parser.add_argument("--verbose",       action="store_true")
    parser.add_argument("--linkedin",      action="store_true", help="Print LinkedIn search URLs")
    parser.add_argument("--glassdoor",     action="store_true", help="Print Glassdoor search URLs")
    parser.add_argument("--researchgate",  action="store_true", help="Print ResearchGate search URLs")
    parser.add_argument("--visa-jobs",     action="store_true", help="Print US visa-sponsoring employer URLs")
    parser.add_argument("--discover-labs", action="store_true", help="Find active PIs via Google Scholar")
    parser.add_argument("--no-save",       action="store_true")
    parser.add_argument("--limit",         type=int, default=40)
    parser.add_argument("--config",        default="config/search_profile.yaml")
    args = parser.parse_args()

    # ── Config ─────────────────────────────────────────────────────────────────
    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(f"Config not found: {args.config}")
        sys.exit(1)

    scorer     = RelevanceScorer(args.config)
    primary_kw = cfg.get("primary_keywords", [])
    roles      = cfg.get("job_settings", {}).get("target_roles", [])
    field      = cfg.get("profile", {}).get("field", "")
    name       = cfg.get("profile", {}).get("name", "")

    if args.sources:
        sources = args.sources
    elif args.mode == "phd":
        sources = PHD_SOURCES
    elif args.mode == "job":
        sources = JOB_SOURCES
    else:
        sources = ALL_SOURCES

    # ── Banner ─────────────────────────────────────────────────────────────────
    if RICH:
        mode_str = {"all": "Jobs + PhD", "phd": "PhD Only", "job": "Jobs Only"}[args.mode]
        console.print(f"\n[bold cyan]╔═══════════════════════════════════════════════╗[/bold cyan]")
        console.print(f"[bold cyan]║   career-radar  ·  {mode_str:<26} ║[/bold cyan]")
        console.print(f"[bold cyan]╚═══════════════════════════════════════════════╝[/bold cyan]")
        if name or field:
            console.print(f"[dim]  {name}  ·  {field}[/dim]")
        console.print(f"[dim]  Keywords: {', '.join(primary_kw[:5])}{'...' if len(primary_kw) > 5 else ''}[/dim]")
        console.print(f"[dim]  Sources ({len(sources)}): {', '.join(sources[:8])}{'...' if len(sources) > 8 else ''}[/dim]\n")

    all_listings: list[Listing] = []

    # ── Job board scrapers ─────────────────────────────────────────────────────
    if any(s in sources for s in JOB_SOURCES):
        if RICH:
            console.print("[bold]── Job Boards ──[/bold]")

        if "indeed" in sources:
            from scrapers.jobs import scrape_indeed
            all_listings += run("Indeed", scrape_indeed, primary_kw, roles)

        if "adzuna" in sources:
            from scrapers.jobs import scrape_adzuna
            for cc in ["gb", "us", "de"]:
                all_listings += run(f"Adzuna ({cc.upper()})", scrape_adzuna, primary_kw, cc)

        if "remoteok" in sources:
            from scrapers.jobs import scrape_remoteok
            all_listings += run("RemoteOK", scrape_remoteok, primary_kw)

        if "arbeitnow" in sources:
            from scrapers.jobs import scrape_arbeitnow
            all_listings += run("Arbeitnow (EU)", scrape_arbeitnow, primary_kw)

        if "weworkremotely" in sources:
            from scrapers.jobs import scrape_weworkremotely
            all_listings += run("WeWorkRemotely", scrape_weworkremotely, primary_kw)

        if "jobicy" in sources:
            from scrapers.extra_sources import scrape_jobicy
            all_listings += run("Jobicy (remote)", scrape_jobicy, primary_kw)

        if "themuse" in sources:
            from scrapers.extra_sources import scrape_the_muse
            all_listings += run("The Muse", scrape_the_muse, primary_kw)

        if "jobspresso" in sources:
            from scrapers.extra_sources import scrape_jobspresso
            all_listings += run("Jobspresso (remote)", scrape_jobspresso, primary_kw)

    # ── PhD / Academic scrapers ────────────────────────────────────────────────
    if any(s in sources for s in PHD_SOURCES):
        if RICH:
            console.print("\n[bold]── PhD & Academic Boards ──[/bold]")

        if "findaphd" in sources:
            from scrapers.phd import scrape_findaphd
            all_listings += run("FindAPhD", scrape_findaphd, primary_kw)

        if "euraxess" in sources:
            from scrapers.phd import scrape_euraxess
            all_listings += run("EurAxess", scrape_euraxess, primary_kw)

        if "phdportal" in sources:
            from scrapers.phd import scrape_phdportal
            all_listings += run("PhDPortal.eu", scrape_phdportal, primary_kw)

        if "embl" in sources:
            from scrapers.phd import scrape_embl
            all_listings += run("EMBL / EBI / Sanger", scrape_embl, primary_kw)

        if "nature" in sources:
            from scrapers.phd import scrape_nature_careers
            all_listings += run("Nature & Science Careers", scrape_nature_careers, primary_kw)

        if "academicpositions" in sources:
            from scrapers.phd import scrape_academic_positions
            all_listings += run("AcademicPositions.com", scrape_academic_positions, primary_kw)

        if "scholar" in sources:
            from scrapers.phd import scrape_scholar_rss
            all_listings += run("Google Scholar RSS", scrape_scholar_rss, primary_kw)

        if "phdscanner" in sources:
            if RICH:
                console.print("  [dim](PhDScanner uses Playwright headless browser — takes ~15s)[/dim]")
            from scrapers.phdscanner import scrape_phdscanner
            all_listings += run("PhDScanner ★", scrape_phdscanner, primary_kw)

        if "jobsacuk" in sources:
            from scrapers.extra_sources import scrape_jobsacuk
            all_listings += run("jobs.ac.uk (UK)", scrape_jobsacuk, primary_kw)

        if "the_jobs" in sources:
            from scrapers.extra_sources import scrape_the_jobs
            all_listings += run("Times Higher Ed", scrape_the_jobs, primary_kw)

        if "higheredjobs" in sources:
            from scrapers.extra_sources import scrape_higheredjobs
            all_listings += run("HigherEdJobs (US)", scrape_higheredjobs, primary_kw)

        if "daad" in sources:
            from scrapers.extra_sources import scrape_daad
            all_listings += run("DAAD (Germany)", scrape_daad, primary_kw)

        if "msca" in sources:
            from scrapers.extra_sources import scrape_msca
            all_listings += run("MSCA / Marie Curie", scrape_msca, primary_kw)

    # ── Manual URL builders ────────────────────────────────────────────────────
    if args.linkedin:
        from scrapers.jobs import get_linkedin_urls
        print_urls("LinkedIn", get_linkedin_urls(primary_kw, roles))

    if args.glassdoor:
        from scrapers.jobs import get_glassdoor_urls
        print_urls("Glassdoor", get_glassdoor_urls(primary_kw))

    if args.researchgate:
        from scrapers.extra_sources import get_researchgate_urls
        print_urls("ResearchGate", get_researchgate_urls(primary_kw))

    if args.visa_jobs:
        from scrapers.extra_sources import get_h1bdata_urls
        print_urls("US Visa-Sponsoring Employers (myvisajobs)", get_h1bdata_urls(primary_kw))

    # ── Score & filter ─────────────────────────────────────────────────────────
    if RICH:
        console.print(f"\n[dim]Scoring {len(all_listings)} listings...[/dim]")

    filtered = scorer.filter(all_listings, mode=args.mode)
    phd_n    = sum(1 for l in filtered if l.listing_type == "phd")
    job_n    = sum(1 for l in filtered if l.listing_type == "job")

    if RICH:
        console.print(
            f"[green]✓[/green] [bold]{len(filtered)}[/bold] passed filter  "
            f"([magenta]{phd_n} PhD[/magenta] · [blue]{job_n} jobs[/blue] · "
            f"min score: {scorer.min_score})\n"
        )

    # ── Display & save ─────────────────────────────────────────────────────────
    print_results_table(filtered, limit=args.limit)

    if args.verbose and filtered:
        if RICH:
            console.print("\n[bold]── Full Details (top results) ──[/bold]\n")
        print_verbose(filtered, limit=min(10, args.limit))

    if args.discover_labs:
        if RICH:
            console.print("\n[bold cyan]── Lab Discovery (Google Scholar) ──[/bold cyan]\n")
        try:
            from scrapers.phd import scrape_scholar_rss
            # Reuse scholar RSS for quick discovery summary
            labs_listings = scrape_scholar_rss(primary_kw[:3], max_results=5)
            for l in labs_listings:
                if RICH:
                    console.print(f"  [bold]{l.title[:60]}[/bold]")
                    console.print(f"  [dim]{l.url}[/dim]\n")
        except Exception as e:
            print(f"  Lab discovery: {e}")

    if not args.no_save and filtered:
        csv_path = save_csv(filtered)
        md_path  = save_markdown(filtered)
        if RICH:
            console.print(f"\n[green]💾 Saved:[/green]  {csv_path}  |  {md_path}")
        else:
            print(f"\nSaved:\n  {csv_path}\n  {md_path}")

    if RICH:
        console.print(
            f"\n[bold green]Done.[/bold green]  "
            f"[magenta]{phd_n} PhD[/magenta]  +  [blue]{job_n} jobs[/blue]  found.\n"
        )
    else:
        print(f"\nDone. {phd_n} PhD + {job_n} jobs found.")


if __name__ == "__main__":
    main()
