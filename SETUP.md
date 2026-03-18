# Auburn Blueprint Group Scraper

Finds every Auburn-related Facebook group and Reddit community,
dumps everything into a formatted Excel sheet.

## Setup (Windows)

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Optionally add FB_EMAIL and FB_PASSWORD for deeper Facebook search
```

## Run

```bash
python scrape.py
```

Excel file saves to `/exports/auburn_blueprint_outreach_TIMESTAMP.xlsx`

## What It Does

**Phase 1 — Google/Bing/DuckDuckGo dorking** (no login needed)
Search engines independently index public FB groups. Queries like
`site:facebook.com/groups "Auburn" "Mobile"` surface groups that
Facebook's own search hides. 50+ queries across 3 engines.

**Phase 2 — Deep Facebook search** (requires FB login in .env)
300+ search term variations: 17 cities x 20 Auburn terms.
Also does chain discovery — finds a group, follows its related groups sidebar.

**Phase 3 — Reddit**
Scans r/AuburnUniversity, city subreddits (r/Birmingham, r/Huntsville, etc.),
parent/college subs. No login needed.

## Excel Sheets

| Sheet | Contents |
|---|---|
| Stats Dashboard | Summary numbers |
| Facebook Groups | Every group URL, city, clickable link |
| Reddit Subreddits | Auburn-relevant communities |
| Reddit Posts | Specific posts to engage with |

## Cities Covered

Alabama: Mobile, Huntsville, Birmingham, Montgomery, Tuscaloosa, Dothan,
Decatur, Gadsden, Auburn, Anniston, Florence, Phenix City

Florida: Pensacola
Georgia: Atlanta (north suburbs), Columbus
Tennessee: Nashville, Memphis
