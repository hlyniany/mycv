# Upwork Profile Scraping

**Date:** 2026-06-10  
**Status:** ✅ Working — Bright Data Web Unlocker API successfully bypasses Cloudflare

---

## Quick Start

```bash
# Run the scraper (reads API key from upwork/api.json)
cd <repo_root>
python3 upwork/scrape_profiles.py
```

Results saved to `upwork/upwork_parsed.db`.

---

## Configuration

API credentials are read from **`upwork/api.json`**:

```json
{
    "brightdata_api_key": "your_key_here",
    "brightdata_zone":    "web_unlocker1"
}
```

- Get a free key at **https://brightdata.com** (5,000 free credits/month, no credit card)
- Create a **Web Unlocker API** zone in the Bright Data Control Panel → Web Access APIs
- 1 credit = 1 URL; 160 profiles ≈ 160–320 credits (with retries)

Environment variable overrides (optional):
```bash
BRIGHTDATA_API_KEY=your_key BRIGHTDATA_ZONE=web_unlocker1 python3 upwork/scrape_profiles.py
SOURCE_DB=path/to/input.db OUTPUT_DB=path/to/output.db DELAY=3 python3 upwork/scrape_profiles.py
```

---

## Architecture

```
upwork_profiles.db          scrape_profiles.py          upwork_parsed.db
(160 profile URLs)  ──→  [Bright Data Unlocker API]  ──→  raw_pages table
                            ↓ raw HTML (1–1.7MB)           profiles table
                         [Node.js vm.runInNewContext]
                            ↓ window.__NUXT__ JSON
                         [parse + regex fallbacks]
                            ↓ structured fields
```

---

## How It Works

### 1. Fetching (`fetch_page`)

Sends a POST to `https://api.brightdata.com/request`:

```python
{
    "zone":   "web_unlocker1",
    "url":    "https://www.upwork.com/freelancers/~01abc...",
    "format": "raw"   # returns full HTML, including window.__NUXT__
}
```

Bright Data handles residential proxy rotation, Cloudflare bypass, and CAPTCHA solving automatically. `render_js` is not needed since Upwork SSR-renders `window.__NUXT__` server-side.

### 2. Parsing (`parse_html`)

Two-stage extraction:

**Stage 1 — Node.js `vm.runInNewContext`** (primary, full data):
- Writes NUXT script to a temp `.js` file (avoids shell-escaping issues)
- Evaluates in Node.js sandbox
- Data path: `state.profileViewer.profile` ← **correct path** (not `state.profile.profile`)

**Stage 2 — Regex fallbacks** (for fields missing after eval):
- `country`, `city`, `totalHoursActual`, `totalJobsWorked`, `memberSince`
- `prefLabel` skill labels, work history titles from the args block

### 3. Retry logic

`MAX_RETRIES = 3`. On HTTP error, timeout, or missing `__NUXT__` — waits 5s and retries.

---

## Output Schema (`upwork_parsed.db`)

### Table: `profiles`

| Column | Type | Source |
|---|---|---|
| `source_url` | TEXT | input URL |
| `name` / `first_name` | TEXT | `profile.name` |
| `title` | TEXT | `profile.title` |
| `overview` | TEXT | `profile.description` |
| `country` / `city` | TEXT | `profile.location` |
| `country_code_iso2` | TEXT | `profile.location` |
| `hourly_rate` / `currency` | REAL/TEXT | `stats.hourlyRate` |
| `total_hours` | REAL | `stats.totalHoursActual` |
| `total_jobs` | INTEGER | `stats.totalJobsWorked` |
| `total_feedback` | INTEGER | `stats.totalFeedback` |
| `rating` | REAL | `stats.rating` |
| `nss_score` | INTEGER | `stats.nSS100BwScore` |
| `top_rated_status` | TEXT | `stats.topRatedStatus` (`top_rated`, `hipo`, …) |
| `member_since` | TEXT | `stats.memberSince` (ISO8601) |
| `last_worked_on` | TEXT | `stats.lastWorkedOn` |
| `response_state` | TEXT | `stats.responsiveState` |
| `hire_again_pct` | REAL | `stats.hireAgainPercentage` |
| `availability_nid` | TEXT | `availability.capacity.nid` (`fullTime`, `partTime`, …) |
| `skills` | JSON | `specializedProfilesInfo[].selectedSkills[]` |
| `portfolio` | JSON | `portfolios[]` — title, description, type, url |
| `languages` / `education` / `certificates` | JSON | respective arrays |
| `employment_history` / `other_experiences` | JSON | respective arrays |
| `job_categories` | JSON | `jobCategoriesV2` |
| `work_history_titles` | JSON | regex from NUXT args block |
| `photo_url` | TEXT | `profile.portrait.portrait` |
| `video_url` | TEXT | `video` field |
| `uid` / `ciphertext` | TEXT | `identity` |
| `parse_error` | TEXT | NULL if parsed OK |

### Table: `raw_pages`

| Column | Description |
|---|---|
| `url` | Profile URL |
| `html` | zlib-compressed full HTML blob |
| `http_status` | HTTP status code |
| `fetched_at` | ISO8601 timestamp |
| `proxy_used` | `brightdata:web_unlocker1` |
| `error` | NULL if successful |

---

## Verified Results (manual test, 2026-06-10)

| Profile | Name | Country | Rating | NSS | Jobs | Hours | Rate |
|---|---|---|---|---|---|---|---|
| andriyfreyik | Andriy F. | Ukraine, Lviv | 4.30 | 1 | 21 | 86.6h | $40 |
| denyss57 | Denys S. | Ukraine, Kyiv | 5.0 | 1 | 15 | 695.5h | $35 |

Both parsed with `parse_error = NULL`.

---

## Key Technical Notes

- **NUXT data path:** `window.__NUXT__.state.profileViewer.profile`  
  (documented path `state.profile.profile` is **wrong** for current Upwork frontend)
- **`video` field** is a plain string URL, not an object
- **`portrait`** lives at `profile.profile.portrait`, not `profile.portrait`
- **NSS score** (`nSS100BwScore`) evaluates to `1` even for 100% JSS profiles — this appears to be Upwork's internal representation; the visible "100%" badge is computed differently
- **Response size:** ~1.3–1.7 MB per profile page

---

## Files

| File | Description |
|---|---|
| `upwork/scrape_profiles.py` | Main scraper + parser |
| `upwork/upwork_profiles.db` | 160 input profile URLs |
| `upwork/upwork_parsed.db` | Output: parsed profiles + raw HTML |
| `upwork/api.json` | API keys (not committed) |
| `upwork/upwork_profile_fields.md` | Full field reference |
| `upwork/collect_upwork_profiles.py` | How URLs were collected (Telegram) |
