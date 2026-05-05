# Career-Radar

A configurable CLI tool that scrapes job listings and funded PhD positions across **21 platforms**, filtered by a personal keyword profile. Works for **any field** — just edit the YAML config.

![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?logo=linux&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-supported-success?logo=linux&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-supported-success?logo=apple&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-supported-success?logo=windows&logoColor=white)

---

## Features

- **Any field**: bioinformatics, software engineering, data science, finance, chemistry, design — configure with keywords
- **21 sources**: see full table below
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
python main.py --sources phdscanner findaphd euraxess jobsacuk msca daad

# Full details for top results
python main.py --verbose

# Print search URLs to open manually (sites that block scrapers)
python main.py --linkedin --glassdoor --researchgate

# US visa-sponsoring employer search
python main.py --visa-jobs

# Find active PIs in your field (cold email targets)
python main.py --discover-labs

# Combine flags
python main.py --mode phd --sources phdscanner findaphd euraxess daad msca --verbose
python main.py --mode job --sources indeed jobicy remoteok arbeitnow --limit 60

# Different profile
python main.py --config config/example_profiles.yaml
```

---

## All Sources

### Job Boards (8 scrapers)

| Source | Method | Coverage | Notes |
|--------|--------|----------|-------|
| **Indeed** | RSS | Global | USA, UK, Canada, Germany |
| **Adzuna** | RSS | Multi-country | GB, US, DE, AU, CA, FR, NL scraped simultaneously |
| **RemoteOK** | JSON API | Remote worldwide | Tech, data, biotech — free API |
| **Arbeitnow** | JSON API | Europe | Germany, Austria, Switzerland, Netherlands focus |
| **WeWorkRemotely** | RSS | Remote worldwide | Curated; tech, design, data |
| **Jobicy** | JSON API | Remote worldwide | Research, data science, biotech — free API |
| **The Muse** | JSON API | USA focus | Company culture + jobs — free API |
| **Jobspresso** | RSS | Remote worldwide | Curated remote roles |
| **LinkedIn** | URL builder | Global | Scraping blocked; opens browser search |
| **Glassdoor** | URL builder | Global | Scraping blocked; opens browser search |

### PhD & Academic Boards (13 scrapers)

| Source | Method | Coverage | Notes |
|--------|--------|----------|-------|
| **PhDScanner** ★ | Playwright + API interception | Global | Requires `playwright install chromium` |
| **FindAPhD** | HTML | UK / Global | Largest PhD listing board worldwide |
| **EurAxess** | RSS + HTML | Europe | Official EU researcher portal |
| **PhDPortal.eu** | HTML | Europe | Major EU PhD aggregator |
| **EMBL / EBI / Sanger** | RSS | Germany, UK | Top-tier European research institutes; always funded |
| **Nature Careers** | RSS | Global | Academic/research scientist positions |
| **Science Careers** | RSS | Global | AAAS journal job board |
| **AcademicPositions.com** | HTML | Europe | EU university research + faculty |
| **jobs.ac.uk** | RSS | UK | Largest UK academic job board |
| **Times Higher Ed** | RSS | Global | Senior academic + research fellow roles |
| **HigherEdJobs** | RSS | USA | Largest US university research job board |
| **DAAD** | HTML | Germany | German Academic Exchange — always funded |
| **MSCA / Marie Curie** | RSS | Europe | Most prestigious EU fellowships — always funded |
| **Google Scholar Alerts** | RSS | Global | Requires manual setup (5 min) — see below |
| **ResearchGate** | URL builder | Global | Login required; opens browser |

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
│   ├── jobs.py                      # Indeed, Adzuna, RemoteOK, Arbeitnow, WWR
│   ├── phd.py                       # FindAPhD, EurAxess, EMBL, Nature, etc.
│   ├── phdscanner.py                # PhDScanner (Playwright + API interception)
│   └── extra_sources.py             # Jobicy, jobs.ac.uk, THE, DAAD, MSCA, Muse
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
