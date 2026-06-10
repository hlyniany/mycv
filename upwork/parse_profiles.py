#!/usr/bin/env python3
"""
Upwork profile parser — reads raw HTML from upwork_parsed.db and extracts
structured profile data into the profiles table.

Run after scrape_profiles.py (or while it's still running — picks up whatever
raw HTML is available). Re-parses ALL raw pages to ensure new fields are populated.

Usage:
    python3 upwork/parse_profiles.py

Env vars:
    OUTPUT_DB   — path to DB (default: upwork/upwork_parsed.db)
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DB = os.environ.get("OUTPUT_DB", os.path.join(BASE_DIR, "upwork_parsed.db"))


# ── Database setup ─────────────────────────────────────────────────────────────

PROFILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url          TEXT NOT NULL UNIQUE,
    fetched_at          TEXT,
    parse_error         TEXT,

    -- identity
    uid                 TEXT,
    ciphertext          TEXT,
    user_id             TEXT,
    contractor_tier     INTEGER,

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
    total_hours_rounded REAL,
    total_hours_recent  REAL,
    total_jobs          INTEGER,
    total_jobs_recent   INTEGER,
    total_feedback      INTEGER,
    total_feedback_recent INTEGER,
    rating              REAL,
    rating_recent       REAL,
    nss_score           INTEGER,
    top_rated_status    TEXT,
    top_rated_plus_status TEXT,
    total_hourly_jobs   INTEGER,
    total_fixed_jobs    INTEGER,
    total_portfolio_items INTEGER,
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
    skills              TEXT,
    languages           TEXT,
    education           TEXT,
    certificates        TEXT,
    employment_history  TEXT,
    portfolio           TEXT,
    job_categories      TEXT,
    other_experiences   TEXT,
    work_history_titles TEXT
)
"""

# New columns added in this version (for migration of existing DBs)
NEW_COLUMNS = [
    ("contractor_tier", "INTEGER"),
    ("total_hours_rounded", "REAL"),
    ("total_hours_recent", "REAL"),
    ("total_jobs_recent", "INTEGER"),
    ("total_feedback_recent", "INTEGER"),
    ("rating_recent", "REAL"),
    ("top_rated_plus_status", "TEXT"),
    ("total_hourly_jobs", "INTEGER"),
    ("total_fixed_jobs", "INTEGER"),
    ("total_portfolio_items", "INTEGER"),
]


def init_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(PROFILES_SCHEMA)
    con.commit()

    # Migrate: add new columns if table already existed without them
    existing = {row[1] for row in con.execute("PRAGMA table_info(profiles)")}
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing:
            con.execute(f"ALTER TABLE profiles ADD COLUMN {col_name} {col_type}")
    con.commit()
    return con


# ── Parsing helpers ────────────────────────────────────────────────────────────

def _meta(html: str, prop: str, attr: str = "property") -> str | None:
    m = re.search(
        rf'<meta[^>]+{attr}="{re.escape(prop)}"[^>]+content="([^"]*)"',
        html,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            rf'<meta[^>]+content="([^"]*)"[^>]+{attr}="{re.escape(prop)}"',
            html,
            re.IGNORECASE,
        )
    return m.group(1) if m else None


def eval_nuxt(nuxt_script: str) -> dict | None:
    """Evaluate window.__NUXT__ in Node.js sandbox and return the JSON."""
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


def _json_or_none(obj) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, (list, dict)) and not obj:
        return None
    return json.dumps(obj)


# ── Main parse logic ───────────────────────────────────────────────────────────

def parse_html(html: str, source_url: str) -> dict:
    result: dict = {"source_url": source_url}

    # ── Meta tags (fast, reliable) ─────────────────────────────────────────
    result["name"] = _meta(html, "og:title")
    result["profile_url"] = _meta(html, "og:url")
    result["title"] = _meta(html, "og:description")
    result["photo_url"] = _meta(html, "twitter:image", "name")

    rate = _meta(html, "product:price:amount")
    result["hourly_rate"] = float(rate) if rate else None
    result["currency"] = _meta(html, "product:price:currency")

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
    """
    try:
        pv = data["state"]["profileViewer"]
        pp = pv["profile"]
    except (KeyError, TypeError):
        return

    if pp is None:
        return

    # identity (inside pp.profile)
    profile_obj = pp.get("profile") or {}
    identity = profile_obj

    r.setdefault("uid", identity.get("uid") or pp.get("uid"))
    r.setdefault("ciphertext", identity.get("ciphertext"))
    r["user_id"] = identity.get("userId")
    r["id_badge_status"] = identity.get("idBadgeStatus")
    r["contractor_tier"] = identity.get("contractorTier")

    # profile core fields
    r.setdefault("name", profile_obj.get("name"))
    r["first_name"] = profile_obj.get("firstName")
    r.setdefault("title", profile_obj.get("title"))
    r["overview"] = (profile_obj.get("description") or "").replace("\\n", "\n")
    r.setdefault("profile_url", pp.get("profileUrl"))
    r["vanity_url"] = pp.get("vanityUrl")
    r["video_url"] = pp.get("video") if isinstance(pp.get("video"), str) else (pp.get("video") or {}).get("videoUrl")
    r["hide_earnings"] = int(bool(pp.get("hideEarnings")))

    # portrait
    portrait = profile_obj.get("portrait") or pp.get("portrait") or {}
    if isinstance(portrait, str):
        r.setdefault("photo_url", portrait)
    else:
        r.setdefault("photo_url", portrait.get("portrait"))

    # location
    loc = profile_obj.get("location") or {}
    r["country"] = loc.get("country")
    r["city"] = loc.get("city")
    r["country_code_iso2"] = loc.get("countryCodeIso2")
    r["timezone_name"] = loc.get("countryTimezone")
    r["timezone_offset"] = loc.get("timezoneOffset")
    r.setdefault("world_region", loc.get("worldRegion"))

    # stats
    stats = pp.get("stats") or {}
    r.setdefault("hourly_rate", (stats.get("hourlyRate") or {}).get("amount"))
    r.setdefault("currency", (stats.get("hourlyRate") or {}).get("currencyCode"))
    r["total_hours"] = stats.get("totalHoursActual") or stats.get("totalHours")
    r["total_hours_rounded"] = stats.get("totalHours")
    r["total_hours_recent"] = stats.get("totalHoursRecent")
    r["total_jobs"] = stats.get("totalJobsWorked")
    r["total_jobs_recent"] = stats.get("totalJobsWorkedRecent")
    r["total_feedback"] = stats.get("totalFeedback")
    r["total_feedback_recent"] = stats.get("totalFeedbackRecent")
    r["rating"] = stats.get("rating")
    r["rating_recent"] = stats.get("ratingRecent")
    r["nss_score"] = stats.get("nSS100BwScore")
    r["top_rated_status"] = stats.get("topRatedStatus")
    r["top_rated_plus_status"] = stats.get("topRatedPlusStatus")
    r["total_hourly_jobs"] = stats.get("totalHourlyJobs")
    r["total_fixed_jobs"] = stats.get("totalFixedJobs")
    r["total_portfolio_items"] = stats.get("totalPortfolioItems")
    r["member_since"] = stats.get("memberSince")
    r["last_worked_on"] = stats.get("lastWorkedOn")
    r["nss_last_calculated"] = stats.get("nssLastCalculated")
    r["response_state"] = stats.get("responsiveState")
    r["total_earnings"] = stats.get("totalEarnings")
    r["hire_again_pct"] = stats.get("hireAgainPercentage")
    r["recommended"] = int(bool(stats.get("recommended")))
    r["english_level"] = stats.get("englishLevel")

    # availability
    avail = pp.get("availability") or {}
    cap = avail.get("capacity") or {}
    r["availability_nid"] = cap.get("nid")
    r["availability_name"] = cap.get("name")

    # skills from specializedProfilesInfo
    skills = []
    for sp in pp.get("specializedProfilesInfo") or []:
        for sk in sp.get("selectedSkills") or []:
            skills.append(sk)
    r["skills"] = json.dumps(skills) if skills else None

    # arrays
    r["languages"] = _json_or_none(pp.get("languages"))
    r["education"] = _json_or_none(pp.get("education"))
    r["certificates"] = _json_or_none(pp.get("certificates"))
    r["employment_history"] = _json_or_none(pp.get("employmentHistory"))
    r["other_experiences"] = _json_or_none(pp.get("otherExperiences"))

    # portfolio
    portfolios = pp.get("portfolios") or []
    portfolio_out = []
    for item in portfolios:
        portfolio_out.append({
            "title": item.get("title"),
            "description": item.get("description"),
            "type": item.get("type"),
            "url": item.get("embeddedLinkUrl") or item.get("imageMiddle"),
        })
    r["portfolio"] = json.dumps(portfolio_out) if portfolio_out else None

    # job categories
    r["job_categories"] = _json_or_none(pp.get("jobCategories") or pp.get("jobCategoriesV2"))


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


# ── Upsert ─────────────────────────────────────────────────────────────────────

ALL_COLS = [
    "source_url", "fetched_at", "parse_error",
    "uid", "ciphertext", "user_id", "contractor_tier",
    "name", "first_name", "title", "overview", "profile_url", "vanity_url",
    "photo_url", "video_url", "hide_earnings",
    "hourly_rate", "currency",
    "total_hours", "total_hours_rounded", "total_hours_recent",
    "total_jobs", "total_jobs_recent",
    "total_feedback", "total_feedback_recent",
    "rating", "rating_recent",
    "nss_score", "top_rated_status", "top_rated_plus_status",
    "total_hourly_jobs", "total_fixed_jobs", "total_portfolio_items",
    "member_since", "last_worked_on",
    "nss_last_calculated", "response_state", "total_earnings",
    "hire_again_pct", "recommended", "english_level", "id_badge_status",
    "country", "city", "country_code_iso2", "timezone_name",
    "timezone_offset", "world_region",
    "availability_nid", "availability_name",
    "skills", "languages", "education", "certificates",
    "employment_history", "portfolio", "job_categories",
    "other_experiences", "work_history_titles",
]


def upsert_profile(con: sqlite3.Connection, data: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    data.setdefault("fetched_at", now)
    values = [data.get(c) for c in ALL_COLS]
    placeholders = ", ".join("?" * len(ALL_COLS))
    update_cols = [c for c in ALL_COLS if c != "source_url"]
    updates = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    con.execute(
        f"""
        INSERT INTO profiles ({', '.join(ALL_COLS)})
        VALUES ({placeholders})
        ON CONFLICT(source_url) DO UPDATE SET {updates}
        """,
        values,
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Output DB  : {OUTPUT_DB}")
    print()

    con = init_db(OUTPUT_DB)

    # Get all raw pages with successful fetch
    rows = con.execute(
        "SELECT url, html, fetched_at FROM raw_pages WHERE http_status = 200 AND html IS NOT NULL"
    ).fetchall()

    print(f"Raw pages to parse: {len(rows)}")
    if not rows:
        print("No raw pages found. Run scrape_profiles.py first.")
        return

    parsed_ok = 0
    parsed_err = 0

    for idx, (url, html_blob, fetched_at) in enumerate(rows, 1):
        # Decompress
        try:
            html = zlib.decompress(html_blob).decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  [{idx:3}/{len(rows)}] ✗ {url[-50:]} decompress_error:{e}")
            upsert_profile(con, {"source_url": url, "parse_error": f"decompress_error:{e}"})
            parsed_err += 1
            continue

        # Parse
        try:
            profile = parse_html(html, url)
            profile.setdefault("fetched_at", fetched_at)
        except Exception as e:
            profile = {"source_url": url, "parse_error": f"parse_exception:{e}"}

        upsert_profile(con, profile)

        name = profile.get("name") or "?"
        title = profile.get("title") or ""
        err = profile.get("parse_error") or ""

        if err:
            parsed_err += 1
            icon = "⚠"
        else:
            parsed_ok += 1
            icon = "✓"

        print(f"  [{idx:3}/{len(rows)}] {icon} {name[:25]:25} | {title[:35]}"
              + (f" [{err}]" if err else ""))

    con.commit()

    # Summary
    total = con.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
    success = con.execute("SELECT COUNT(*) FROM profiles WHERE parse_error IS NULL").fetchone()[0]
    print(f"\n── Done ──────────────────────────────────────────────────")
    print(f"Total profiles : {total}")
    print(f"Parsed OK      : {parsed_ok} (this run)")
    print(f"Parse errors   : {parsed_err} (this run)")
    print(f"All-time OK    : {success}")
    print(f"Output DB      : {OUTPUT_DB}")


if __name__ == "__main__":
    main()
