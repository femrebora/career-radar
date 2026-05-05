# Career-Radar

A configurable CLI tool that scrapes job listings and funded PhD positions across **8 active platforms**, filtered by a personal keyword profile. Works for **any field** — just edit the YAML config.

![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?logo=linux&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-supported-success?logo=linux&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-supported-success?logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-supported-success?logo=windows&logoColor=white)

---

## Features

- **Any field**: bioinformatics, software engineering, data science, finance, chemistry, design — configure with keywords
- **8 active sources**: see full table below
- **Dual mode**: jobs + PhD positions simultaneously, or separately
- **PhDScanner support**: headless Playwright scraper with API interception
- **Relevance scoring**: weighted keyword scoring (0–100) with country and funding bonuses
- **Rich terminal output**: color-coded table, score, salary/funding, experience level
- **Export**: timestamped CSV + Markdown reports saved to `outputs/`
- **No API keys required** for all sources

---

## Quick Start

```bash
git clone https://github.com/Femrebora/career-radar.git
cd career-radar

conda create -n career-radar python=3.11 -y
conda activate career-radar
pip install -r requirements.txt

# PhDScanner support (optional but recommended)
playwright install chromium

# Edit your search profile
nano config/search_profile.yaml

# Run
python main.py
```

---

## Usage

```bash
# All sources (jobs + PhD)
python main.py

# PhD positions only
python main.py --mode phd

# Job listings only  
python main.py --mode job

# Specific sources only
python main.py --sources phdscanner remoteok arbeitnow jobicy

# Full details for top results
python main.py --verbose

# Print search URLs to open manually (sites that block scrapers)
python main.py --linkedin --glassdoor --researchgate

# US visa-sponsoring employer search
python main.py --visa-jobs

# Combine flags
python main.py --mode phd --sources phdscanner scholar --verbose
python main.py --mode job --sources remoteok arbeitnow jobicy adzuna --limit 60

# Different profile
python main.py --config config/example_profiles.yaml
```

---

## Active Sources

### Job Boards (6 scrapers)

| Source | Method | Coverage | Notes |
|--------|--------|----------|-------|
| **Adzuna** | RSS | Multi-country | GB, US, DE, AU, CA, FR, NL |
| **RemoteOK** | JSON API | Remote worldwide | Tech, data, biotech — free API |
| **Arbeitnow** | JSON API | Europe | Germany, Austria, Switzerland, Netherlands |
| **WeWorkRemotely** | RSS | Remote worldwide | Curated remote tech, design, data roles |
| **Jobicy** | JSON API | Remote worldwide | Research, data science, biotech — free API |
| **The Muse** | JSON API | USA focus | Company culture + jobs — free API |
| **LinkedIn** | URL builder | Global | Scraping blocked — opens browser search |
| **Glassdoor** | URL builder | Global | Scraping blocked — opens browser search |

### PhD & Academic Boards (2 scrapers)

| Source | Method | Coverage | Notes |
|--------|--------|----------|-------|
| **PhDScanner** ★ | Playwright + API interception | Global | Requires `playwright install chromium` |
| **Google Scholar Alerts** | RSS | Global | Requires manual setup — see below |

### Unavailable Sources

The following sources were removed because their RSS feeds were discontinued or they now block automated access. They may be restored in a future release using Playwright.

| Source | Reason |
|--------|--------|
| Indeed | Blocked scrapers (403) in 2022 |
| FindAPhD | Cloudflare bot protection |
| EurAxess | RSS feed discontinued (404) |
| EMBL / EBI / Sanger | RSS feeds discontinued (404) |
| Nature Careers | RSS feed discontinued (404) |
| Science Careers | RSS feed discontinued (404) |
| DAAD | URL changed, HTML blocked |
| MSCA / Marie Curie | RSS feed discontinued (404) |
| jobs.ac.uk | RSS returns empty results |
| Times Higher Ed | RSS returns empty results |
| HigherEdJobs | RSS returns newsletter digest, not jobs |
| Jobspresso | RSS feed dead |
| PhDPortal.eu | Bot protection |
| AcademicPositions | Bot protection |
| ResearchGate | Login required — URL builder only |

---

## Configuration

Edit `config/search_profile.yaml`:

```yaml
profile:
  name: "Your Name"
  field: "Bioinformatics"

primary_keywords:          # +15 pts each (max 60)
  - "bioinformatics"
  - "cancer genomics"
  - "CRISPR"

secondary_keywords:        # +5 pts each (max 20)
  - "Python"
  - "Nextflow"
  - "NGS"

exclude_keywords:          # score → 0 if matched
  - "veterinary"
  - "plant biology"

preferred_countries:       # +10 pts bonus
  - "Germany"
  - "UK"
  - "Netherlands"

phd_settings:
  funded_only: true        # only funded PhD positions

job_settings:
  target_roles:
    - "Bioinformatics Scientist"
    - "Research Scientist"
  experience_levels: ["Entry", "Mid", "Postdoc"]

min_relevance_score: 40    # 0–100
```

See `config/example_profiles.yaml` for Software Engineering, Data Science, Molecular Biology, and Quantitative Finance profiles.

---

## PhDScanner — Playwright Setup

PhDScanner is a React SPA with no public API. The scraper uses Playwright to:
1. Launch headless Chromium
2. Intercept XHR/fetch API calls made by the React app
3. Parse the raw JSON response (fast path)
4. Fall back to DOM scraping if no API is found

```bash
# One-time setup
pip install playwright
playwright install chromium

# Run
python main.py --sources phdscanner
```

---

## Google Scholar Alerts Setup (Optional)

1. Go to [scholar.google.com/scholar_alerts](https://scholar.google.com/scholar_alerts)
2. Create alerts for your keywords
3. Click the RSS icon on each alert
4. Paste URLs into `config/scholar_rss_feeds.txt`

---

## Output

```
outputs/
  results_20250504_143022.csv    # all fields, sortable in Excel / pandas
  results_20250504_143022.md     # formatted Markdown report
```

---

## Project Structure

```
career-radar/
├── main.py                          # CLI — all sources wired here
├── requirements.txt
├── config/
│   ├── search_profile.yaml          # your profile (edit this)
│   ├── example_profiles.yaml        # example profiles for 4 fields
│   └── scholar_rss_feeds.txt        # Google Scholar alert RSS URLs
├── scrapers/
│   ├── utils.py                     # shared helpers
│   ├── jobs.py                      # Adzuna, RemoteOK, Arbeitnow, WWR
│   ├── phd.py                       # Scholar RSS + legacy scrapers (archived)
│   ├── phdscanner.py                # PhDScanner (Playwright + API interception)
│   └── extra_sources.py             # Jobicy, The Muse, and URL builders
├── filters/
│   ├── scorer.py                    # relevance scoring engine
│   └── output.py                    # terminal table + CSV/MD export
└── outputs/                         # auto-created, gitignored
```

---

## Weekly Cron

```bash
# crontab -e
0 9 * * 1 cd /path/to/career-radar && conda run -n career-radar python main.py
```

---

## License

MIT
