#!/usr/bin/env python3
"""
Upwork profile scraper via Bright Data Web Unlocker API.

Fetches ~160 Upwork profile pages through Bright Data (bypasses Cloudflare
and all bot-protection), extracts full profile data using Node.js
window.__NUXT__ eval + meta-tag regex, stores results in upwork_parsed.db.

Usage:
    python3 upwork/scrape_profiles.py

API key is read from upwork/api.json (field "brightdata_api_key"):
    {
        "brightdata_api_key": "your_key_here",
        "brightdata_zone":    "web_unlocker1"   <- optional, default: web_unlocker1
    }

You can also override via environment variables:
    BRIGHTDATA_API_KEY=your_key python3 upwork/scrape_profiles.py
    BRIGHTDATA_ZONE=my_zone    python3 upwork/scrape_profiles.py

Other optional env vars:
    SOURCE_DB   — path to source DB with URLs (default: upwork/upwork_profiles.db)
    OUTPUT_DB   — path to output DB          (default: upwork/upwork_parsed.db)
    DELAY       — seconds between requests   (default: 2)
    SKIP_RAW    — set to 1 to skip storing raw HTML blobs

Cost: 1 credit per request (Bright Data free tier: 5,000 credits/month).
160 profiles ≈ 160–320 credits (with retries).
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import zlib
from datetime import datetime, timezone

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_config() -> tuple[str, str]:
    """Return (api_key, zone_name): env vars take priority over api.json."""
    key  = os.environ.get("BRIGHTDATA_API_KEY", "")
    zone = os.environ.get("BRIGHTDATA_ZONE", "")

    if not key or not zone:
        candidates = [
            os.path.join(BASE_DIR, "api.json"),
            os.path.join(os.path.dirname(BASE_DIR), "upwork", "api.json"),
            # also check the canonical mycv repo location (for worktree usage)
            os.path.expanduser("~/Documents/GitHub/mycv/upwork/api.json"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                with open(candidate) as f:
                    data = json.load(f)
                key  = key  or data.get("brightdata_api_key", "")
                zone = zone or data.get("brightdata_zone", "web_unlocker1")
                break

    zone = zone or "web_unlocker1"
    return key, zone


BRIGHTDATA_API_KEY, BRIGHTDATA_ZONE = _load_config()
SOURCE_DB  = os.environ.get("SOURCE_DB",  os.path.join(BASE_DIR, "upwork_profiles.db"))
OUTPUT_DB  = os.environ.get("OUTPUT_DB",  os.path.join(BASE_DIR, "upwork_parsed.db"))
DELAY      = float(os.environ.get("DELAY", "2"))
SKIP_RAW   = os.environ.get("SKIP_RAW", "0") == "1"

BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"

REQUEST_TIMEOUT = 120  # seconds — Bright Data can be slow on protected pages
MAX_RETRIES     = 3


# ── Database setup ─────────────────────────────────────────────────────────────

def init_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_pages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            url          TEXT    NOT NULL UNIQUE,
            html         BLOB,
            http_status  INTEGER,
            fetched_at   TEXT,
            proxy_used   TEXT,
            error        TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url          TEXT NOT NULL UNIQUE,
            fetched_at          TEXT,
            parse_error         TEXT,

            -- identity
            uid                 TEXT,
            ciphertext          TEXT,
            user_id             TEXT,

            -- profile
            name                TEXT,
            first_name          TEXT,
            title               TEXT,
            overview            TEXT,
            profile_url         TEXT,
            vanity_url          TEXT,
            photo_url           TEXT,
            video_url           TEXT,
            hide_earnings       INTEGER,

            -- stats
            hourly_rate         REAL,
            currency            TEXT,
            total_hours         REAL,
            total_jobs          INTEGER,
            total_feedback      INTEGER,
            rating              REAL,
            nss_score           INTEGER,
            top_rated_status    TEXT,
            member_since        TEXT,
            last_worked_on      TEXT,
            nss_last_calculated TEXT,
            response_state      TEXT,
            total_earnings      REAL,
            hire_again_pct      REAL,
            recommended         INTEGER,
            english_level       TEXT,
            id_badge_status     TEXT,

            -- location
            country             TEXT,
            city                TEXT,
            country_code_iso2   TEXT,
            timezone_name       TEXT,
            timezone_offset     INTEGER,
            world_region        TEXT,

            -- availability
            availability_nid    TEXT,
            availability_name   TEXT,

            -- JSON arrays
            skills              TEXT,   -- JSON array of {ontologyId, prefLabel}
            languages           TEXT,   -- JSON array
            education           TEXT,   -- JSON array
            certificates        TEXT,   -- JSON array
            employment_history  TEXT,   -- JSON array
            portfolio           TEXT,   -- JSON array of {title, description, type, url}
            job_categories      TEXT,   -- JSON array
            other_experiences   TEXT,   -- JSON array
            work_history_titles TEXT    -- JSON array of contract titles (regex)
        )
    """)
    con.commit()
    return con


# ── Fetching via Bright Data Web Unlocker ─────────────────────────────────────

def fetch_page(url: str, session: requests.Session) -> tuple[str, int]:
    """Fetch URL through Bright Data Web Unlocker API. Returns (html, status_code).

    Bright Data automatically handles residential proxy rotation, Cloudflare
    challenges, CAPTCHA solving and browser fingerprinting.
    Cost: 1 credit per successful request (free tier: 5,000/month).
    """
    resp = session.post(
        BRIGHTDATA_ENDPOINT,
        headers={
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "zone": BRIGHTDATA_ZONE,
            "url": url,
            "format": "raw",
        },
        timeout=REQUEST_TIMEOUT,
    )
    return resp.text, resp.status_code


# ── Parsing ────────────────────────────────────────────────────────────────────

def _meta(html: str, prop: str, attr: str = "property") -> str | None:
    m = re.search(
        rf'<meta[^>]+{attr}="{re.escape(prop)}"[^>]+content="([^"]*)"',
        html,
        re.IGNORECASE,
    )
    if not m:
        # Try reversed attr/content order
        m = re.search(
            rf'<meta[^>]+content="([^"]*)"[^>]+{attr}="{re.escape(prop)}"',
            html,
            re.IGNORECASE,
        )
    return m.group(1) if m else None


def eval_nuxt(nuxt_script: str) -> dict | None:
    """Evaluate window.__NUXT__ in Node.js sandbox and return the JSON.

    Uses temp files to avoid shell-escaping issues with repr().
    """
    import tempfile
    runner = (
        "const vm = require('vm'), fs = require('fs');\n"
        "const sandbox = { window: {} };\n"
        "try {\n"
        "  const src = fs.readFileSync(process.argv[1] + '.nuxt.js', 'utf8');\n"
        "  vm.runInNewContext(src, sandbox);\n"
        "  process.stdout.write(JSON.stringify(sandbox.window.__NUXT__ || null));\n"
        "} catch(e) {\n"
        "  process.stdout.write(JSON.stringify({__error: e.message}));\n"
        "}\n"
    )
    try:
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as tf:
            tf.write(runner)
            js_file = tf.name
        nuxt_file = js_file + ".nuxt.js"
        with open(nuxt_file, "w", encoding="utf-8") as nf:
            nf.write(nuxt_script)
        r = subprocess.run(
            ["node", js_file],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0 or not r.stdout:
            return None
        data = json.loads(r.stdout)
        if isinstance(data, dict) and "__error" in data:
            return None
        return data
    except Exception:
        return None
    finally:
        for p in (js_file, nuxt_file):
            try:
                os.unlink(p)
            except Exception:
                pass


def parse_html(html: str, source_url: str) -> dict:
    result: dict = {"source_url": source_url}

    # ── Meta tags (fast, reliable) ─────────────────────────────────────────
    result["name"]        = _meta(html, "og:title")
    result["profile_url"] = _meta(html, "og:url")
    result["title"]       = _meta(html, "og:description")
    result["photo_url"]   = _meta(html, "twitter:image", "name")

    rate = _meta(html, "product:price:amount")
    result["hourly_rate"] = float(rate) if rate else None
    result["currency"]    = _meta(html, "product:price:currency")

    t = re.search(r"Upwork Freelancer from ([^<]+)</title>", html)
    if t:
        result["world_region"] = t.group(1).strip()

    uid = re.search(r"/persons/(\d+)/", html)
    result["uid"] = uid.group(1) if uid else None

    cipher = re.search(r"/freelancers/(~[0-9a-f]+)", html)
    result["ciphertext"] = cipher.group(1) if cipher else None

    # ── Extract NUXT script ────────────────────────────────────────────────
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
    nuxt_script = next(
        (s for s in scripts if "window.__NUXT__" in s and len(s) > 5000), ""
    )

    if not nuxt_script:
        result["parse_error"] = "no_nuxt_script"
        return result

    # ── Try Node.js eval first ─────────────────────────────────────────────
    nuxt_data = eval_nuxt(nuxt_script)
    if nuxt_data:
        try:
            _parse_nuxt_data(nuxt_data, result)
        except Exception as e:
            result["parse_error"] = f"nuxt_parse_error:{e}"
    else:
        result["parse_error"] = "nuxt_eval_failed"

    # ── Regex fallbacks for key fields ─────────────────────────────────────
    _regex_fallbacks(nuxt_script, result)

    return result


def _parse_nuxt_data(data: dict, r: dict) -> None:
    """Extract fields from evaluated window.__NUXT__ object.

    Path: state.profileViewer.profile
    Within that object:
      .profile  → core profile fields (name, title, description, location, portrait, ...)
      .stats    → stats (rating, nss, hours, ...)
      .identity → identity fields
      .portrait is also at top level of profileViewer.profile
    """
    try:
        pv = data["state"]["profileViewer"]
        pp = pv["profile"]           # profileViewer.profile
    except (KeyError, TypeError):
        return

    # identity (inside pp.profile)
    profile_obj = pp.get("profile") or {}
    identity = profile_obj  # identity fields live in pp.profile

    r.setdefault("uid",         identity.get("uid") or pp.get("uid"))
    r.setdefault("ciphertext",  identity.get("ciphertext"))
    r["user_id"]         = identity.get("userId")
    r["id_badge_status"] = identity.get("idBadgeStatus")

    # profile core fields
    r.setdefault("name",        profile_obj.get("name"))
    r["first_name"]   = profile_obj.get("firstName")
    r.setdefault("title",       profile_obj.get("title"))
    r["overview"]     = (profile_obj.get("description") or "").replace("\\n", "\n")
    r.setdefault("profile_url", pp.get("profileUrl"))
    r["vanity_url"]   = pp.get("vanityUrl")
    r["video_url"]    = pp.get("video") if isinstance(pp.get("video"), str) else (pp.get("video") or {}).get("videoUrl")
    r["hide_earnings"] = int(bool(pp.get("hideEarnings")))

    # portrait (at pp.profile.portrait, not pp.portrait)
    portrait = profile_obj.get("portrait") or pp.get("portrait") or {}
    if isinstance(portrait, str):
        r.setdefault("photo_url", portrait)
    else:
        r.setdefault("photo_url", portrait.get("portrait"))

    # location (inside pp.profile.location)
    loc = profile_obj.get("location") or {}
    r["country"]           = loc.get("country")
    r["city"]              = loc.get("city")
    r["country_code_iso2"] = loc.get("countryCodeIso2")
    r["timezone_name"]     = loc.get("countryTimezone")
    r["timezone_offset"]   = loc.get("timezoneOffset")
    r.setdefault("world_region", loc.get("worldRegion"))

    # stats (at pp level)
    stats = pp.get("stats") or {}
    r.setdefault("hourly_rate",  (stats.get("hourlyRate") or {}).get("amount"))
    r.setdefault("currency",     (stats.get("hourlyRate") or {}).get("currencyCode"))
    r["total_hours"]         = stats.get("totalHoursActual") or stats.get("totalHours")
    r["total_jobs"]          = stats.get("totalJobsWorked")
    r["total_feedback"]      = stats.get("totalFeedback")
    r["rating"]              = stats.get("rating")
    r["nss_score"]           = stats.get("nSS100BwScore")
    r["top_rated_status"]    = stats.get("topRatedStatus")
    r["member_since"]        = stats.get("memberSince")
    r["last_worked_on"]      = stats.get("lastWorkedOn")
    r["nss_last_calculated"] = stats.get("nssLastCalculated")
    r["response_state"]      = stats.get("responsiveState")
    r["total_earnings"]      = stats.get("totalEarnings")
    r["hire_again_pct"]      = stats.get("hireAgainPercentage")
    r["recommended"]         = int(bool(stats.get("recommended")))
    r["english_level"]       = stats.get("englishLevel")

    # availability
    avail = pp.get("availability") or {}
    cap = avail.get("capacity") or {}
    r["availability_nid"]  = cap.get("nid")
    r["availability_name"] = cap.get("name")

    # skills from specializedProfilesInfo
    skills = []
    for sp in pp.get("specializedProfilesInfo") or []:
        for sk in sp.get("selectedSkills") or []:
            skills.append(sk)
    r["skills"] = json.dumps(skills) if skills else None

    # arrays
    r["languages"]          = _json_or_none(pp.get("languages"))
    r["education"]          = _json_or_none(pp.get("education"))
    r["certificates"]       = _json_or_none(pp.get("certificates"))
    r["employment_history"] = _json_or_none(pp.get("employmentHistory"))
    r["other_experiences"]  = _json_or_none(pp.get("otherExperiences"))

    # portfolio
    portfolios = pp.get("portfolios") or []
    portfolio_out = []
    for item in portfolios:
        portfolio_out.append({
            "title":       item.get("title"),
            "description": item.get("description"),
            "type":        item.get("type"),
            "url":         item.get("embeddedLinkUrl") or item.get("imageMiddle"),
        })
    r["portfolio"] = json.dumps(portfolio_out) if portfolio_out else None

    # job categories
    r["job_categories"] = _json_or_none(pp.get("jobCategories") or pp.get("jobCategoriesV2"))


def _json_or_none(obj) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, (list, dict)) and not obj:
        return None
    return json.dumps(obj)


def _regex_fallbacks(nuxt: str, r: dict) -> None:
    """Fill in fields that may be missing after NUXT eval failure."""
    if not r.get("country"):
        m = re.search(r'country:"([^"]+)"', nuxt)
        r["country"] = m.group(1) if m else None

    if not r.get("city") and not r.get("world_region"):
        m = re.search(r'worldRegion:"([^"]+)"', nuxt)
        r["world_region"] = m.group(1) if m else None

    if not r.get("total_hours"):
        m = re.search(r'totalHoursActual:([\d.]+)', nuxt)
        r["total_hours"] = float(m.group(1)) if m else None

    if not r.get("total_jobs"):
        m = re.search(r'totalJobsWorked:(\d+)', nuxt)
        r["total_jobs"] = int(m.group(1)) if m else None

    if not r.get("member_since"):
        m = re.search(r'memberSince:"([^"]+)"', nuxt)
        r["member_since"] = m.group(1) if m else None

    if not r.get("nss_score"):
        m = re.search(r'"nSS100BwScore":(\d+)', nuxt)
        r["nss_score"] = int(m.group(1)) if m else None

    if not r.get("overview"):
        bio = re.search(r'"(I (?:help|am|work|build|create|specialize)[^"]{100,})"', nuxt)
        r["overview"] = bio.group(1).replace("\\n", "\n") if bio else None

    if not r.get("skills"):
        labels = re.findall(r'prefLabel:"([^"]+)"', nuxt)
        if labels:
            r["skills"] = json.dumps([{"prefLabel": lb} for lb in labels])

    # Work history titles from args block
    args_block = nuxt[nuxt.rfind("}("):]
    titles = re.findall(r'"([A-Z][^"]{15,120})"', args_block)
    if titles:
        r["work_history_titles"] = json.dumps(titles)


# ── Main scraping loop ─────────────────────────────────────────────────────────

def upsert_raw(con: sqlite3.Connection, url: str, html: bytes | None,
               status: int | None, proxy: str, error: str | None) -> None:
    blob = zlib.compress(html) if (html and not SKIP_RAW) else None
    con.execute(
        """
        INSERT INTO raw_pages (url, html, http_status, fetched_at, proxy_used, error)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            html=excluded.html, http_status=excluded.http_status,
            fetched_at=excluded.fetched_at, proxy_used=excluded.proxy_used,
            error=excluded.error
        """,
        (url, blob, status, datetime.now(timezone.utc).isoformat(), proxy, error),
    )
    con.commit()


def upsert_profile(con: sqlite3.Connection, data: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    cols = [
        "source_url", "fetched_at", "parse_error",
        "uid", "ciphertext", "user_id",
        "name", "first_name", "title", "overview", "profile_url", "vanity_url",
        "photo_url", "video_url", "hide_earnings",
        "hourly_rate", "currency",
        "total_hours", "total_jobs", "total_feedback", "rating",
        "nss_score", "top_rated_status", "member_since", "last_worked_on",
        "nss_last_calculated", "response_state", "total_earnings",
        "hire_again_pct", "recommended", "english_level", "id_badge_status",
        "country", "city", "country_code_iso2", "timezone_name",
        "timezone_offset", "world_region",
        "availability_nid", "availability_name",
        "skills", "languages", "education", "certificates",
        "employment_history", "portfolio", "job_categories",
        "other_experiences", "work_history_titles",
    ]
    data.setdefault("fetched_at", now)
    values = [data.get(c) for c in cols]
    placeholders = ", ".join("?" * len(cols))
    update_cols = [c for c in cols if c != "source_url"]
    updates = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    con.execute(
        f"""
        INSERT INTO profiles ({', '.join(cols)})
        VALUES ({placeholders})
        ON CONFLICT(source_url) DO UPDATE SET {updates}
        """,
        values,
    )
    con.commit()


def main() -> None:
    if not BRIGHTDATA_API_KEY:
        sys.exit(
            "ERROR: Bright Data API key not found.\n"
            "  Add to upwork/api.json:\n"
            '    { "brightdata_api_key": "your_key_here" }\n'
            "  Or set env var: BRIGHTDATA_API_KEY=your_key\n"
            "  Get a free key (5,000 credits/month) at https://brightdata.com"
        )

    print(f"Source DB  : {SOURCE_DB}")
    print(f"Output DB  : {OUTPUT_DB}")
    print(f"Mode       : Bright Data Web Unlocker (zone: {BRIGHTDATA_ZONE})")
    print(f"Delay      : {DELAY}s between requests")
    print()

    # Load URLs
    src = sqlite3.connect(SOURCE_DB)
    urls = [row[0] for row in src.execute("SELECT url FROM upwork_profiles ORDER BY id")]
    src.close()
    print(f"Loaded {len(urls)} URLs")

    out = init_db(OUTPUT_DB)

    # Skip already-parsed profiles
    done_urls = set(
        row[0]
        for row in out.execute(
            "SELECT source_url FROM profiles WHERE parse_error IS NULL OR parse_error NOT LIKE 'fetch_%'"
        )
    )
    pending = [u for u in urls if u not in done_urls]
    print(f"Pending    : {len(pending)} (skipping {len(done_urls)} already done)")
    print(f"Credits est: ~{len(pending)}–{len(pending)*3} credits (1/req, up to {MAX_RETRIES} retries)")
    print()

    session = requests.Session()

    for idx, url in enumerate(pending, 1):
        # Normalise URL
        norm_url = url.strip().rstrip("/")
        if norm_url.startswith("http://"):
            norm_url = "https://" + norm_url[7:]
        if not norm_url.startswith("https://www.upwork.com"):
            norm_url = norm_url.replace("https://upwork.com", "https://www.upwork.com")
            norm_url = norm_url.replace("http://www.upwork.com", "https://www.upwork.com")

        print(f"[{idx:3}/{len(pending)}] {norm_url[:80]}", flush=True, end=" ")

        html_text = None
        status    = None
        error     = None

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                time.sleep(5)
            try:
                html_text, status = fetch_page(norm_url, session)

                if status == 200 and len(html_text) > 5000 and "window.__NUXT__" in html_text:
                    error = None
                    break
                elif status == 200 and len(html_text) > 5000:
                    # Got HTML but no NUXT — maybe we need JS render
                    error = "no_nuxt_in_response"
                    break
                elif status == 429:
                    error = "rate_limited"
                    time.sleep(30)
                else:
                    error = f"http_{status}"
            except requests.exceptions.Timeout:
                error = "timeout"
            except Exception as e:
                error = f"fetch_error:{type(e).__name__}"

        # Delay between requests (ScrapingBee has its own rate limits)
        time.sleep(DELAY)

        # Save raw HTML
        upsert_raw(out, norm_url,
                   html_text.encode("utf-8", errors="replace") if html_text else None,
                   status, f"brightdata:{BRIGHTDATA_ZONE}", error)

        if not html_text or status not in (200,):
            print(f"✗ {error}")
            upsert_profile(out, {"source_url": norm_url, "parse_error": error or "no_html"})
            continue

        # Parse
        try:
            profile = parse_html(html_text, norm_url)
        except Exception as e:
            profile = {"source_url": norm_url, "parse_error": f"parse_exception:{e}"}

        upsert_profile(out, profile)

        name  = profile.get("name") or "?"
        title = profile.get("title") or ""
        err   = profile.get("parse_error") or ""
        icon  = "✓" if not err else "⚠"
        print(f"{icon} {name} | {title[:40]}" + (f" [{err}]" if err else ""))

    # Summary
    total   = out.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    success = out.execute("SELECT COUNT(*) FROM profiles WHERE parse_error IS NULL").fetchone()[0]
    print(f"\n── Done ──────────────────────────────────────────────────")
    print(f"Total profiles : {total}")
    print(f"Parsed OK      : {success}")
    print(f"Output DB      : {OUTPUT_DB}")


if __name__ == "__main__":
    main()
