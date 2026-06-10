#!/usr/bin/env python3
"""
Upwork profile fetcher via Bright Data Web Unlocker API (multi-threaded).

Fetches Upwork profile pages through Bright Data (bypasses Cloudflare
and all bot-protection), stores raw HTML in upwork_parsed.db.
Parsing is done separately by parse_profiles.py.

Usage:
    python3 upwork/scrape_profiles.py

Env vars:
    WORKERS     — concurrent fetch threads (default: 5, auto-reduces on 429)
    SOURCE_DB   — path to source DB with URLs (default: upwork/upwork_profiles.db)
    OUTPUT_DB   — path to output DB          (default: upwork/upwork_parsed.db)
    DELAY       — seconds between requests per thread (default: 2)

Cost: 1 credit per request (Bright Data free tier: 5,000 credits/month).
"""

import json
import os
import sqlite3
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_config() -> tuple[str, str]:
    """Return (api_key, zone_name): env vars take priority over api.json."""
    key = os.environ.get("BRIGHTDATA_API_KEY", "")
    zone = os.environ.get("BRIGHTDATA_ZONE", "")

    if not key or not zone:
        candidates = [
            os.path.join(BASE_DIR, "api.json"),
            os.path.join(os.path.dirname(BASE_DIR), "upwork", "api.json"),
            os.path.expanduser("~/Documents/GitHub/mycv/upwork/api.json"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                with open(candidate) as f:
                    data = json.load(f)
                key = key or data.get("brightdata_api_key", "")
                zone = zone or data.get("brightdata_zone", "web_unlocker1")
                break

    zone = zone or "web_unlocker1"
    return key, zone


BRIGHTDATA_API_KEY, BRIGHTDATA_ZONE = _load_config()
SOURCE_DB = os.environ.get("SOURCE_DB", os.path.join(BASE_DIR, "upwork_profiles.db"))
OUTPUT_DB = os.environ.get("OUTPUT_DB", os.path.join(BASE_DIR, "upwork_parsed.db"))
DELAY = float(os.environ.get("DELAY", "2"))
WORKERS = int(os.environ.get("WORKERS", "5"))

BRIGHTDATA_ENDPOINT = "https://api.brightdata.com/request"
REQUEST_TIMEOUT = 120
MAX_RETRIES = 3


# ── Adaptive concurrency ──────────────────────────────────────────────────────

class AdaptiveConcurrency:
    """Tracks 429 responses and signals workers to back off globally."""

    def __init__(self):
        self._lock = threading.Lock()
        self._429_count = 0
        self._429_window_start = time.time()
        self._WINDOW_SEC = 60
        self._THRESHOLD = 3
        self._backoff_until = 0.0

    def report_429(self):
        with self._lock:
            now = time.time()
            if now - self._429_window_start > self._WINDOW_SEC:
                self._429_count = 0
                self._429_window_start = now
            self._429_count += 1
            if self._429_count >= self._THRESHOLD:
                self._backoff_until = now + 60
                self._429_count = 0
                print(f"\n⚠ Rate limited {self._THRESHOLD}x in {self._WINDOW_SEC}s"
                      f" — all threads backing off 60s")

    def wait_if_backing_off(self):
        """Block calling thread if global backoff is active."""
        while True:
            with self._lock:
                remaining = self._backoff_until - time.time()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 5))


# ── Database setup ─────────────────────────────────────────────────────────────

def init_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path, check_same_thread=False)
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
    con.commit()
    return con


# ── URL normalisation ──────────────────────────────────────────────────────────

def normalise_url(url: str) -> str:
    norm = url.strip().rstrip("/")
    if norm.startswith("http://"):
        norm = "https://" + norm[7:]
    if not norm.startswith("https://www.upwork.com"):
        norm = norm.replace("https://upwork.com", "https://www.upwork.com")
        norm = norm.replace("http://www.upwork.com", "https://www.upwork.com")
    return norm


# ── Fetching ───────────────────────────────────────────────────────────────────

def fetch_page(url: str, session: requests.Session, force_render: bool = False) -> tuple[str, int]:
    """Fetch URL through Bright Data Web Unlocker API.

    If force_render=True, passes x-unblock-expect header to force browser
    rendering and wait for profile data to hydrate. Requires 'Custom Web
    Unlocker API' enabled in the Bright Data Control Panel.
    """
    payload: dict = {
        "zone": BRIGHTDATA_ZONE,
        "url": url,
        "format": "raw",
    }
    if force_render:
        # Wait for text that only appears in fully-hydrated NUXT with real data
        payload["headers"] = {
            "x-unblock-expect": '{"text": "totalJobsWorked"}'
        }

    resp = session.post(
        BRIGHTDATA_ENDPOINT,
        headers={
            "Authorization": f"Bearer {BRIGHTDATA_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    return resp.text, resp.status_code


def _has_profile_data(html: str) -> bool:
    """Check if HTML contains a real profile (not a skeleton page).

    Skeleton pages have window.__NUXT__ but profileViewer.profile is null.
    Real pages have NUXT scripts > 20KB with actual profile data.
    """
    # Quick heuristic: find NUXT script and check its size
    idx = html.find("window.__NUXT__")
    if idx == -1:
        return False
    # Find the <script> containing it — check if the block is substantial
    # A real profile NUXT is 60-100KB; skeleton is ~7KB
    script_start = html.rfind("<script", 0, idx)
    script_end = html.find("</script>", idx)
    if script_start == -1 or script_end == -1:
        return False
    nuxt_size = script_end - script_start
    return nuxt_size > 20_000


def fetch_one(url: str, concurrency: AdaptiveConcurrency) -> dict:
    """Fetch a single URL with retries. Returns result dict for main thread."""
    norm_url = normalise_url(url)
    session = requests.Session()
    html_text = None
    http_status = None
    error = None

    for attempt in range(MAX_RETRIES):
        concurrency.wait_if_backing_off()
        if attempt > 0:
            time.sleep(5 + attempt * 5)
        try:
            # On retry after skeleton page, force browser rendering
            force = (attempt > 0 and error == "skeleton_page")
            html_text, http_status = fetch_page(norm_url, session, force_render=force)

            if http_status == 200 and _has_profile_data(html_text):
                error = None
                break
            elif http_status == 200:
                # Got HTML but skeleton/no NUXT data — retry with rendering
                error = "skeleton_page"
                time.sleep(10 + attempt * 10)
            elif http_status == 429:
                error = "rate_limited"
                concurrency.report_429()
                time.sleep(30 + attempt * 15)
            else:
                error = f"http_{http_status}"
        except requests.exceptions.Timeout:
            error = "timeout"
        except Exception as e:
            error = f"fetch_error:{type(e).__name__}"

    time.sleep(DELAY)

    return {
        "url": norm_url,
        "html": html_text,
        "status": http_status,
        "error": error,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BRIGHTDATA_API_KEY:
        sys.exit(
            "ERROR: Bright Data API key not found.\n"
            "  Add to upwork/api.json:\n"
            '    { "brightdata_api_key": "your_key_here" }\n'
            "  Or set env var: BRIGHTDATA_API_KEY=your_key"
        )

    print(f"Source DB  : {SOURCE_DB}")
    print(f"Output DB  : {OUTPUT_DB}")
    print(f"Mode       : Bright Data Web Unlocker (zone: {BRIGHTDATA_ZONE})")
    print(f"Workers    : {WORKERS}")
    print(f"Delay      : {DELAY}s per thread")
    print()

    # Load URLs
    src = sqlite3.connect(SOURCE_DB)
    urls = [row[0] for row in src.execute("SELECT url FROM upwork_profiles ORDER BY id")]
    src.close()
    print(f"Loaded {len(urls)} URLs")

    out = init_db(OUTPUT_DB)

    # Skip already-fetched pages that parsed OK.
    # Pages with parse errors (skeleton pages) will be re-fetched.
    done_urls = set()
    try:
        # If profiles table exists, use parse results to determine what's good
        done_urls = set(
            row[0] for row in out.execute(
                "SELECT source_url FROM profiles WHERE parse_error IS NULL"
            )
        )
    except sqlite3.OperationalError:
        # No profiles table yet — fall back to raw_pages with large blobs
        done_urls = set(
            row[0] for row in out.execute(
                "SELECT url FROM raw_pages WHERE http_status = 200 AND html IS NOT NULL"
            )
        )
    pending = [u for u in urls if normalise_url(u) not in done_urls]
    print(f"Pending    : {len(pending)} (skipping {len(done_urls)} already OK)")
    print(f"Credits est: ~{len(pending)}-{len(pending) * MAX_RETRIES}")
    print()

    if not pending:
        print("Nothing to fetch. Run parse_profiles.py to parse raw HTML.")
        return

    concurrency = AdaptiveConcurrency()
    db_lock = threading.Lock()
    completed = 0
    total = len(pending)

    def store_result(result: dict):
        nonlocal completed
        url = result["url"]
        html_text = result["html"]
        http_status = result["status"]
        error = result["error"]

        blob = None
        if html_text:
            blob = zlib.compress(html_text.encode("utf-8", errors="replace"))

        with db_lock:
            out.execute(
                """
                INSERT INTO raw_pages (url, html, http_status, fetched_at, proxy_used, error)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    html=excluded.html, http_status=excluded.http_status,
                    fetched_at=excluded.fetched_at, proxy_used=excluded.proxy_used,
                    error=excluded.error
                """,
                (url, blob, http_status, datetime.now(timezone.utc).isoformat(),
                 f"brightdata:{BRIGHTDATA_ZONE}", error),
            )
            out.commit()
            completed += 1

        icon = "✓" if http_status == 200 and not error else "✗"
        nuxt = "NUXT" if html_text and "window.__NUXT__" in html_text else "no-nuxt"
        print(f"  [{completed:3}/{total}] {icon} ...{url[-45:]} [{http_status or '?'}] {nuxt}"
              + (f" ERR:{error}" if error else ""))

    # Multi-threaded fetch
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {}
            for url in pending:
                f = executor.submit(fetch_one, url, concurrency)
                futures[f] = url

            for future in as_completed(futures):
                try:
                    result = future.result()
                    store_result(result)
                except Exception as e:
                    url = futures[future]
                    print(f"  ✗ ...{url[-45:]} EXCEPTION: {e}")
                    with db_lock:
                        out.execute(
                            """
                            INSERT INTO raw_pages (url, html, http_status, fetched_at, proxy_used, error)
                            VALUES (?, NULL, NULL, ?, ?, ?)
                            ON CONFLICT(url) DO UPDATE SET
                                error=excluded.error, fetched_at=excluded.fetched_at
                            """,
                            (normalise_url(url), datetime.now(timezone.utc).isoformat(),
                             f"brightdata:{BRIGHTDATA_ZONE}", f"exception:{e}"),
                        )
                        out.commit()
    except KeyboardInterrupt:
        print(f"\n\n⚠ Interrupted! {completed}/{total} fetched. Safe to restart.")

    # Summary
    total_raw = out.execute("SELECT COUNT(*) FROM raw_pages").fetchone()[0]
    ok_raw = out.execute("SELECT COUNT(*) FROM raw_pages WHERE http_status = 200").fetchone()[0]
    print(f"\n── Done ──────────────────────────────────────────────────")
    print(f"Total raw pages : {total_raw}")
    print(f"HTTP 200        : {ok_raw}")
    print(f"Output DB       : {OUTPUT_DB}")
    print(f"\nNext: python3 upwork/parse_profiles.py")


if __name__ == "__main__":
    main()
