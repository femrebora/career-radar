"""Relevance scoring and filtering engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

import yaml


@dataclass
class Listing:
    title:            str   = ""
    description:      str   = ""
    institution:      str   = ""
    company:          str   = ""
    department:       str   = ""
    location:         str   = ""
    country:          str   = ""
    deadline:         str   = ""
    posted_date:      str   = ""
    salary:           str   = ""
    job_type:         str   = ""
    funded:           bool  = False
    experience_level: str   = ""
    url:              str   = ""
    source:           str   = ""
    listing_type:     Literal["job", "phd"] = "job"
    score:            int   = 0


class RelevanceScorer:
    def __init__(self, config_path: str = "config/search_profile.yaml") -> None:
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        self.primary_kw   = [k.lower() for k in cfg.get("primary_keywords",   [])]
        self.secondary_kw = [k.lower() for k in cfg.get("secondary_keywords", [])]
        self.exclude_kw   = [k.lower() for k in cfg.get("exclude_keywords",   [])]
        self.countries    = [c.lower() for c in cfg.get("preferred_countries", [])]
        self.min_score    = cfg.get("min_relevance_score", 40)
        self.funded_only  = cfg.get("phd_settings", {}).get("funded_only", False)

    def _score(self, listing: Listing) -> int:
        text = f"{listing.title} {listing.description} {listing.institution} {listing.company}".lower()

        if any(k in text for k in self.exclude_kw):
            return 0

        score = 0

        # Primary keywords: +15 each, capped at 60
        primary_hits = sum(1 for k in self.primary_kw if k in text)
        score += min(primary_hits * 15, 60)

        # Secondary keywords: +5 each, capped at 20
        secondary_hits = sum(1 for k in self.secondary_kw if k in text)
        score += min(secondary_hits * 5, 20)

        # Preferred country bonus: +10
        if listing.country and any(c in listing.country.lower() for c in self.countries):
            score += 10

        # Funded PhD bonus: +10
        if listing.listing_type == "phd" and listing.funded:
            score += 10

        return min(score, 100)

    def filter(self, listings: list[Listing], mode: str = "all") -> list[Listing]:
        results: list[Listing] = []
        for listing in listings:
            if mode == "phd" and listing.listing_type != "phd":
                continue
            if mode == "job" and listing.listing_type != "job":
                continue
            if self.funded_only and listing.listing_type == "phd" and not listing.funded:
                continue

            listing.score = self._score(listing)
            if listing.score >= self.min_score:
                results.append(listing)

        return sorted(results, key=lambda l: l.score, reverse=True)
