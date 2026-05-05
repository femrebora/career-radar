"""Terminal display and file export (CSV + Markdown)."""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path

from filters.scorer import Listing

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()
    RICH = True
except ImportError:
    console = None
    RICH = False

_OUTPUTS = Path("outputs")

_CSV_FIELDS = [
    "score", "listing_type", "title", "institution", "company",
    "location", "country", "experience_level", "funded",
    "salary", "deadline", "posted_date", "source", "url",
]


def _score_color(score: int) -> str:
    if score >= 70:
        return "green"
    if score >= 50:
        return "yellow"
    return "red"


def print_results_table(listings: list[Listing], limit: int = 40) -> None:
    shown = listings[:limit]
    if not shown:
        msg = "No results matched your profile."
        if RICH:
            console.print(f"[yellow]{msg}[/yellow]")
        else:
            print(msg)
        return

    if RICH:
        tbl = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            row_styles=["", "dim"],
        )
        tbl.add_column("#",       style="dim",  width=4)
        tbl.add_column("Score",   style="bold", width=7)
        tbl.add_column("Type",    width=5)
        tbl.add_column("Title",   min_width=28, max_width=42)
        tbl.add_column("Org",     min_width=16, max_width=24)
        tbl.add_column("Country", width=12)
        tbl.add_column("Source",  width=18)
        tbl.add_column("Funded",  width=7)

        for i, l in enumerate(shown, 1):
            color     = _score_color(l.score)
            funded_s  = "[green]Yes[/green]" if l.funded else ""
            type_s    = "[magenta]PhD[/magenta]" if l.listing_type == "phd" else "[blue]Job[/blue]"
            org       = (l.institution or l.company or "")[:24]
            country   = (l.country or l.location or "")[:12]
            tbl.add_row(
                str(i),
                f"[{color}]{l.score}[/{color}]",
                type_s,
                l.title[:42],
                org,
                country,
                l.source[:18],
                funded_s,
            )
        console.print(tbl)
        console.print(f"[dim]Showing {len(shown)} of {len(listings)} results[/dim]")
    else:
        print(f"\n{'#':<4} {'Score':<7} {'Type':<5} {'Title':<42} {'Source':<18}")
        print("-" * 82)
        for i, l in enumerate(shown, 1):
            print(f"{i:<4} {l.score:<7} {l.listing_type:<5} {l.title[:42]:<42} {l.source[:18]}")
        print(f"\nShowing {len(shown)} of {len(listings)} results")


def print_verbose(listings: list[Listing], limit: int = 10) -> None:
    for l in listings[:limit]:
        if RICH:
            console.print(f"[bold]{l.title}[/bold]")
            org = l.institution or l.company
            if org:
                console.print(f"  [cyan]{org}[/cyan]  ·  {l.location or l.country}")
            if l.salary:
                console.print(f"  [green]Salary: {l.salary}[/green]")
            if l.deadline:
                console.print(f"  [yellow]Deadline: {l.deadline}[/yellow]")
            if l.funded and l.listing_type == "phd":
                console.print("  [green]Funded[/green]")
            if l.description:
                console.print(f"  [dim]{l.description[:300]}[/dim]")
            console.print(f"  [blue]{l.url}[/blue]\n")
        else:
            print(f"\n{l.title}")
            print(f"  {l.institution or l.company} | {l.location or l.country}")
            print(f"  Score: {l.score}  Source: {l.source}")
            if l.url:
                print(f"  {l.url}")


def save_csv(listings: list[Listing]) -> str:
    _OUTPUTS.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _OUTPUTS / f"results_{ts}.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for l in listings:
            writer.writerow({k: getattr(l, k, "") for k in _CSV_FIELDS})

    return str(path)


def save_markdown(listings: list[Listing]) -> str:
    _OUTPUTS.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _OUTPUTS / f"results_{ts}.md"

    lines = [
        f"# career-radar Results — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**{len(listings)} positions found**",
        "",
        "| # | Score | Type | Title | Organisation | Country | Source | Funded |",
        "|---|-------|------|-------|--------------|---------|--------|--------|",
    ]
    for i, l in enumerate(listings, 1):
        org     = (l.institution or l.company or "")[:30]
        country = (l.country or l.location or "")[:15]
        title   = f"[{l.title[:50]}]({l.url})" if l.url else l.title[:50]
        funded  = "Yes" if l.funded else ""
        lines.append(
            f"| {i} | {l.score} | {l.listing_type} | {title} | {org} | {country} | {l.source} | {funded} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
