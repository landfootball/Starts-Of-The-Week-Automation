# Workflow: Weekly Data Update

## Objective
Automatically scrape and store the latest NFL defensive stats and game odds every Wednesday midnight Sydney time, so graphics are always ready to generate for the week's video.

## Schedule
- **Trigger**: GitHub Actions cron — Tuesday AND Wednesday at 12:00 AM Sydney time (AEDT)
- **Cron**: `0 13 * * 1` (Tuesday midnight Sydney) + `0 13 * * 2` (Wednesday midnight Sydney)
- **File**: `.github/workflows/weekly_update.yml`

## What it does
1. Scrapes TeamRankings.com for all 10 defensive stat pages (all 32 teams, all stats)
2. Calls The Odds API for current week's game totals and team implied totals
3. Commits the updated JSON files to the repo
4. Streamlit app reads the committed files automatically

## Output files
- `data/stats/latest.json` — defensive stats for all 32 teams
- `data/odds/latest.json` — game totals and implied team scores for the current week

## How to trigger manually
1. Go to your GitHub repo → **Actions** tab
2. Click **Weekly Data Update** in the left panel
3. Click **Run workflow** (top right of the workflow runs table)
4. Click the green **Run workflow** button

Useful when:
- You want fresh data mid-week
- The scheduled run failed
- It's pre-season and you're testing

## How to debug a failed run
1. Click on the failed run in GitHub Actions
2. Expand the failed step to see the error
3. Common causes:
   - **TeamRankings rate limit**: The scraper adds 1.2s delays between requests. If it's still getting blocked, increase `time.sleep()` in `tools/scrape_teamrankings.py`
   - **Odds API key missing**: Check that `ODDS_API_KEY` is set in repo secrets (Settings → Secrets and variables → Actions)
   - **Odds API quota**: Free tier = 500 requests/month. Each weekly run uses ~2 requests. You have plenty.

## If TeamRankings changes their page structure
The scraper targets `<table class="tr-table ...">` and the first three `<td>` columns (rank, team, value). If they redesign the site, update `tools/scrape_teamrankings.py` → `_fetch_stat_page()`.
