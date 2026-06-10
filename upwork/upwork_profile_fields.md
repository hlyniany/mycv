# Upwork Freelancer Profile — Field Reference for Parser

> Source: saved HTML page of a public Upwork freelancer profile  
> Example file: `Sergii C. - Klaviyo Email Marketing Expert...html`  
> Framework: Nuxt 2 SSR — profile data is embedded in `window.__NUXT__` JavaScript object

---

## Parsing Strategy Overview

The page has **two data sources**:

1. **`<meta>` tags in `<head>`** — quick access to a small set of key fields; reliable, easy to parse with regex or DOM.
2. **`window.__NUXT__` script** — the full profile data object embedded as a minified/compressed JavaScript function call. Contains all fields. Requires JS evaluation or regex extraction.

The NUXT script looks like:
```js
window.__NUXT__ = (function(a, b, c, ...) {
  // variable assignments
  return { /* state tree */ };
}("value1", "value2", ...));
```
Variables are passed as function arguments and referenced by single/double-letter names inside the body. To parse, use Node.js `vm` module to evaluate in a sandbox, or use a headless browser.

---

## Source 1 — `<meta>` Tags

These are SSR-rendered and reliably present in the saved HTML.

| Field | Meta selector | Example value |
|---|---|---|
| **Display name** | `meta[property="og:title"]` | `Sergii C.` |
| **Profile URL** | `meta[property="og:url"]` | `https://www.upwork.com/freelancers/~01140923f209578a6b` |
| **Professional title** | `meta[property="og:description"]` | `Klaviyo Email Marketing Expert for Shopify \| Flows & Campaigns` |
| **Profile photo (original, S3)** | `meta[property="og:image"]` | `https://s3-us-west-2.amazonaws.com/agora-profile-portraits-prod/...` |
| **Profile photo (CDN, stable)** | `meta[name="twitter:image"]` | `https://www.upwork.com/profile-portraits/c1X_...` |
| **Hourly rate amount** | `meta[property="product:price:amount"]` | `40` |
| **Hourly rate currency** | `meta[property="product:price:currency"]` | `USD` |
| **City + country (in page title)** | `<title>` tag text | `... Freelancer from Kharkiv, Ukraine` |
| **Jobs count (in meta description)** | `meta[name="description"]` | `Sergii has completed 26 jobs on Upwork.` |
| **User UID (in og:image URL path)** | extracted from `og:image` or `og:url` | `1786261915023216640` |
| **Ciphertext ID (in profile URL)** | extracted from `og:url` | `~01140923f209578a6b` |

### Regex patterns for meta tags

```python
import re

# Display name
name = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)

# Profile URL  
url = re.search(r'<meta[^>]+property="og:url"[^>]+content="([^"]+)"', html)

# Professional title (og:description)
title = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)

# Photo URL (stable CDN)
photo = re.search(r'<meta[^>]+name="twitter:image"[^>]+content="([^"]+)"', html)

# Hourly rate
rate = re.search(r'<meta[^>]+property="product:price:amount"[^>]+content="([^"]+)"', html)
currency = re.search(r'<meta[^>]+property="product:price:currency"[^>]+content="([^"]+)"', html)

# City/Country from <title>
city_country = re.search(r'Upwork Freelancer from ([^<]+)</title>', html)
# → "Kharkiv, Ukraine"

# UID from og:image or og:url
uid = re.search(r'/persons/(\d+)/', html)

# Ciphertext from og:url
cipher = re.search(r'/freelancers/(~[a-f0-9]+)', html)
```

---

## Source 2 — `window.__NUXT__` JavaScript Object

Located in a `<script>` tag near the end of `<body>`. Identifying it:

```python
import re

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
nuxt_script = next((s for s in scripts if 'window.__NUXT__' in s and len(s) > 5000), None)
```

> ⚠️ The data is compressed with short variable names (`a`, `b`, `aM`, etc.).  
> Field values are either **string literals** (extractable by regex) or **variable references** (require JS evaluation to resolve).

### Recommended extraction method

**Option A — Node.js sandbox evaluation (reliable, full data):**
```js
const vm = require('vm');
const sandbox = { window: {} };
vm.runInNewContext(nuxtScript, sandbox);
const profile = sandbox.window.__NUXT__.state.profile.profile;
```

**Option B — Python regex on literal values (fast, partial data):**  
Works for fields whose values appear as string literals directly.

---

### Profile Object Path

After evaluation, the main profile object is at:

```
window.__NUXT__.state.profile.lastId  → ciphertext (e.g. "6059573f")
window.__NUXT__.state.profile.profile.identity
window.__NUXT__.state.profile.profile.profile
window.__NUXT__.state.profile.profile.stats
window.__NUXT__.state.profile.profile.location
window.__NUXT__.state.profile.profile.portrait
window.__NUXT__.state.profile.profile.availability
window.__NUXT__.state.profile.profile.portfolios
window.__NUXT__.state.profile.profile.specializedProfilesInfo
window.__NUXT__.state.profile.profile.languages
window.__NUXT__.state.profile.profile.certificates
window.__NUXT__.state.profile.profile.employmentHistory
window.__NUXT__.state.profile.profile.education
window.__NUXT__.state.profile.profile.otherExperiences
window.__NUXT__.state.profile.profile.jobCategories
```

---

### Field Reference — `profile.identity`

| Field | JS path | Type | Description |
|---|---|---|---|
| `uid` | `.identity.uid` | string | Internal numeric user ID (`"1786261915023216640"`) |
| `userId` | `.identity.userId` | string | Short hex user ID (`"6059573f"`) |
| `ciphertext` | `.identity.ciphertext` | string | Profile URL token (`"6059573f"`) |
| `recno` | `.identity.recno` | number | Legacy record number |
| `edcUserId` | `.identity.edcUserId` | string | — |
| `owner` | `.identity.owner` | boolean | Whether current user owns this profile |

---

### Field Reference — `profile.profile` (core profile)

| Field | JS path | Type | Example value | Regex fallback |
|---|---|---|---|---|
| **Name (display)** | `.profile.name` | string | `"Sergii C."` | `og:title` meta |
| **First name** | `.profile.firstName` | string | `"Sergii"` | — |
| **Short name** | `.profile.shortName` | string | `"Sergii C."` | — |
| **Professional title** | `.profile.title` | string | `"Klaviyo Email Marketing Expert for Shopify \| Flows & Campaigns"` | `og:description` meta |
| **Overview / Bio** | `.profile.description` | string | Full Markdown-like text with `\n` line breaks | see regex below |
| **Profile URL** | `.profile.profileUrl` | string | `"https://www.upwork.com/freelancers/~01140923f209578a6b"` | `og:url` meta |
| **Vanity URL** | `.profile.vanityUrl` | string\|null | custom slug or `null` | — |
| **Hide earnings** | `.profile.hideEarnings` | boolean | `false` | — |
| **Video intro URL** | `.profile.videoUrl` | string\|null | YouTube link or `null` | — |

#### Regex for overview/bio text

```python
# The bio appears as a string literal in the NUXT script
bio_match = re.search(r'"(I help [^"]{50,})"', nuxt_script)
# Or more generally — find the description field context:
bio_match = re.search(r'description:"((?:[^"\\]|\\.){100,})"', nuxt_script)
```

---

### Field Reference — `profile.stats`

| Field | JS path | Type | Example value | Notes |
|---|---|---|---|---|
| **Total hours worked** | `.stats.totalHours` | float | `85.166666` | Rounded for display: `85` |
| **Total hours (actual)** | `.stats.totalHoursActual` | float | `85.16` | — |
| **Total hours (recent)** | `.stats.totalHoursRecent` | number | — | Current period only |
| **Total jobs** | `.stats.totalJobsWorked` | number | `26` | All-time |
| **Total jobs (recent)** | `.stats.totalJobsWorkedRecent` | number | — | — |
| **Total feedback count** | `.stats.totalFeedback` | number | `13` | = number of reviews |
| **Total feedback (recent)** | `.stats.totalFeedbackRecent` | number | — | — |
| **Rating** | `.stats.rating` | number | `5.0` | 1–5 scale |
| **Rating (recent)** | `.stats.ratingRecent` | number | — | — |
| **Hourly rate** | `.stats.hourlyRate` | object | `{currencyCode:"USD", amount:40}` | Also in meta tag |
| **Total hourly jobs** | `.stats.totalHourlyJobs` | number | — | — |
| **Total fixed jobs** | `.stats.totalFixedJobs` | number | `27` | — |
| **Member since** | `.stats.memberSince` | string (ISO) | `"2024-05-03T05:10:02.340Z"` | Date of registration |
| **Last worked on** | `.stats.lastWorkedOn` | string (ISO) | `"2026-06-03T00:00:00.000Z"` | Last completed job |
| **NSS score** | `.stats.nSS100BwScore` | number | `100` | Job Success Score (0–100) |
| **NSS last calculated** | `.stats.nssLastCalculated` | string (ISO) | `"2026-06-09T00:00:00.000Z"` | — |
| **Top Rated status** | `.stats.topRatedStatus` | string | `"topRated"` | `"topRated"`, `"topRatedPlus"`, `null` |
| **Top Rated Plus** | `.stats.topRatedPlusStatus` | string\|null | `null` | — |
| **Hire again %** | `.stats.hireAgainPercentage` | number | — | % who would rehire |
| **Response state** | `.stats.responsiveState` | string | `"within_a_day"` | e.g. `"within_a_day"`, `"within_an_hour"` |
| **Portfolio items count** | `.stats.totalPortfolioItems` | number | — | — |
| **English level** | `.stats.englishLevel` | string | — | e.g. `"Basic"`, `"Conversational"`, `"Fluent"`, `"Native"` |
| **Total earnings** | `.stats.totalEarnings` | number\|null | `null` if hidden | Hidden when `hideEarnings: true` |
| **Recommended** | `.stats.recommended` | boolean | `true` | Upwork recommended flag |
| **Contractor tier** | `.stats.contractorTier` (on identity obj) | number | `2` | — |
| **ID badge status** | `.identity.idBadgeStatus` | string | `"PASSED"` | — |

#### Regex fallback for NSS score

```python
jss = re.search(r'"nSS100BwScore":(\d+)', nuxt_script)  # if not minified
# In compressed form, look for the literal value next to context:
jss_context = re.search(r'nSS100BwScore:[a-z_$]+', nuxt_script)  # variable ref
```

---

### Field Reference — `profile.location`

| Field | JS path | Type | Example value |
|---|---|---|---|
| **Country** | `.location.country` | string | `"Ukraine"` |
| **City** | `.location.city` | string | `"Kharkiv"` |
| **State / region** | `.location.state` | string\|null | — |
| **Timezone name** | `.location.countryTimezone` | string | `"UTC (Coordinated Universal Time)"` |
| **World region (display)** | `.location.worldRegion` | string | `"Kharkiv, Ukraine (UTC (Coor)"` |
| **Timezone offset** | `.location.timezoneOffset` | number | `0` (UTC) |
| **ISO-2 country code** | `.location.countryCodeIso2` | string | `"UA"` |
| **ISO-3 country code** | `.location.countryCodeIso3` | string | `"UKR"` |

#### Regex fallback

```python
country = re.search(r'country:"([^"]+)"', nuxt_script)
city = re.search(r'worldRegion:"([^"]+)"', nuxt_script)
# worldRegion gives "City, Country (UTC...)" — parse city from it
```

---

### Field Reference — `profile.portrait`

| Field | JS path | Type | Description |
|---|---|---|---|
| **Portrait (standard)** | `.portrait.portrait` | string URL | ~128px CDN photo |
| **Big portrait** | `.portrait.bigPortrait` | string URL | ~256px |
| **Small portrait** | `.portrait.smallPortrait` | string URL | ~64px |
| **Original (S3)** | `.portrait.originalPortrait` | string URL | Full-res, temporary signed URL |

> **Stable CDN photo** (no expiry): use `twitter:image` meta tag or `portrait`/`bigPortrait` fields.  
> `originalPortrait` URL expires (contains `Expires=` parameter).

---

### Field Reference — `profile.availability`

| Field | JS path | Type | Example value |
|---|---|---|---|
| **Capacity NID** | `.availability.capacity.nid` | string | `"fullTime"`, `"partTime"`, `"asNeeded"` |
| **Capacity display name** | `.availability.capacity.name` | string | `"More than 30 hrs/week"` |
| **Min hours/week** | `.availability.minHours` | number\|null | — |
| **Max hours/week** | `.availability.maxHours` | number\|null | — |
| **Available days** | `.availability.availableDays` | array\|null | — |
| **Availability timestamp** | `.availability.availabilityTimeStamp` | string | creation date |

---

### Field Reference — Skills

Skills appear in two places:

**1. In specialized profiles** — `.specializedProfilesInfo[].selectedSkills[]`

```js
// Each skill object:
{
  skillId: "1031626779570716672",
  freetextAnswer: null
}
```

**2. In the function argument list** — skill objects passed as args:

```js
// Each skill ontology object:
{
  uid: "...",
  entityStatus: "active",
  scopeNote: null,
  ontologyId: "upwork:klaviyo",    // machine-readable skill ID
  prefLabel: "Klaviyo"             // human-readable skill name
}
```

Known skills from this profile's argument list:
- `Klaviyo` (`upwork:klaviyo`)
- `Email Marketing Strategy` (`upwork:emailmarketingstrategy`)
- `Make.com` (`upwork:integromat`)
- `Airtable` (`upwork:airtable`)
- `Design Validation` (`upwork:designvalidation`)
- `Email` (`kg:51-95284`)
- `Email Template` (`kg:51-65118`)

#### Regex for skill labels in NUXT args

```python
# prefLabel appears as string literals in function call arguments
skill_labels = re.findall(r'"((?:Klaviyo|Airtable|Email[^"]{0,40}|Make\.com)[^"]*)"', nuxt_script)
# Or generally extract all prefLabel occurrences:
skill_labels = re.findall(r'prefLabel:"([^"]+)"', nuxt_script)
```

---

### Field Reference — `profile.portfolios[]`

Each portfolio item (project showcase):

| Field | JS path | Type | Description |
|---|---|---|---|
| `uid` | `.uid` | string | Unique item ID |
| `title` | `.title` | string | Project title |
| `description` | `.description` | string | Detailed description with `\n` |
| `attachmentName` | `.attachmentName` | string | Original filename of uploaded image |
| `attachmentSize` | `.attachmentSize` | number | File size in bytes |
| `type` | `.type` | string | `"image"`, `"video"`, `"link"` |
| `imageSmall` | `.imageSmall` | string | Relative URL (`/att/download/portfolio/...`) |
| `imageMiddle` | `.imageMiddle` | string | — |
| `imageLarge` | `.imageLarge` | string | — |
| `imageFixedWidth` | `.imageFixedWidth` | string | Fixed-width thumbnail |
| `videoUrl` | `.videoUrl` | string\|null | YouTube/Vimeo URL |
| `embeddedLinkUrl` | `.embeddedLinkUrl` | string\|null | External project link |
| `projectUid` | `.projectUid` | string | Parent project group ID |
| `creationTs` | `.creationTs` | string (ISO) | Creation timestamp |

> Image URLs are relative. Prefix with `https://www.upwork.com` for full URL.

---

### Field Reference — `profile.specializedProfilesInfo[]`

| Field | JS path | Type | Description |
|---|---|---|---|
| `profileId` | `.profileId` | string | Specialized profile ID |
| `rank` | `.rank` | number | Display order |
| `status` | `.status` | string | `"active"` etc. |
| `occupations[].occupationId` | `.occupations[0].occupationId` | string | Occupation ontology ID |
| `occupations[].prefLabel` | `.occupations[0].prefLabel` | string | e.g. `"Email Marketer"` |
| `selectedSkills[].skillId` | `.selectedSkills[i].skillId` | string | Skill ontology ID |

---

### Fields Present but Empty in this Profile

These fields exist in the data structure but are `null` / empty array for this freelancer:

| Field | JS path | Likely populated when |
|---|---|---|
| Languages | `.languages` | Freelancer fills in Languages section |
| Certificates | `.certificates` | Freelancer adds certificates |
| Employment history | `.employmentHistory` | Freelancer adds work experience |
| Education | `.education` | Freelancer adds education |
| Other experiences | `.otherExperiences` | Freelancer adds other experience |
| ESN | `.esn` | — |
| Client relationship | `.clientRelationship` | Viewed by logged-in client |

---

### Work History / Contract Reviews

Work history appears in the NUXT args as title strings. Examples from this profile:
- `"Feather Baby – December Klaviyo Campaigns, Reactivation & Deliverability Warm-Up"`
- `"Intelligent Organism Email automation"`
- `"Klaviyo List Cleanup, Flow Setup, and Reactivation Project"`
- `"LinkedIn, Snov.io, Lead generation, outreach"`
- `"SPF, DKIM, DMARC Fix + Email Warm-up Setup"`
- `"Feather Baby Spring Email Campaigns (March–May 2026)"`

Each contract object (after JS evaluation) typically contains:
- `title` — job title
- `amount` — contract value
- `feedback` — client review text
- `rating` — contract rating
- `startDate` / `endDate`
- `clientCountry`

---

## Parsing Implementation Notes

### 1. Evaluating `window.__NUXT__` in Python

```python
import subprocess, json, re

# Extract the NUXT script
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
nuxt_script = next((s for s in scripts if 'window.__NUXT__' in s and len(s) > 5000), None)

# Write to temp file, eval with Node.js
node_code = f"""
const window = {{}};
{nuxt_script}
process.stdout.write(JSON.stringify(window.__NUXT__));
"""
result = subprocess.run(['node', '-e', node_code], capture_output=True, text=True)
data = json.loads(result.stdout)
profile = data['state']['profile']['profile']['profile']
```

### 2. Quick regex-only extraction (no JS eval)

```python
def parse_upwork_html(html):
    def meta(prop, attr='property'):
        m = re.search(rf'<meta[^>]+{attr}="{re.escape(prop)}"[^>]+content="([^"]+)"', html)
        return m.group(1) if m else None

    # From meta tags (fast & reliable)
    result = {
        'name':         meta('og:title'),
        'profile_url':  meta('og:url'),
        'title':        meta('og:description'),
        'photo_url':    meta('twitter:image', 'name'),
        'hourly_rate':  meta('product:price:amount'),
        'currency':     meta('product:price:currency'),
    }

    # City/country from page <title>
    t = re.search(r'Upwork Freelancer from ([^<]+)</title>', html)
    result['location'] = t.group(1).strip() if t else None

    # UIDs from URL
    result['uid'] = (re.search(r'/persons/(\d+)/', html) or [None, None])[1]
    result['ciphertext'] = (re.search(r'/freelancers/(~[0-9a-f]+)', html) or [None, None])[1]

    # Extract NUXT script for deeper fields
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    nuxt = next((s for s in scripts if 'window.__NUXT__' in s and len(s) > 5000), '')

    # Bio / overview (literal string in NUXT args)
    bio = re.search(r'"(I (?:help|am|work|build|create|specialize)[^"]{100,})"', nuxt)
    result['overview'] = bio.group(1).replace('\\n', '\n') if bio else None

    # Location from NUXT
    country = re.search(r'country:"([^"]+)"', nuxt)
    city = re.search(r'worldRegion:"([^"]+)"', nuxt)
    result['country'] = country.group(1) if country else None
    result['world_region'] = city.group(1) if city else None

    # Stats
    result['total_hours'] = float((re.search(r'totalHoursActual:([\d.]+)', nuxt) or [None, '0'])[1])
    result['total_jobs'] = int((re.search(r'totalJobsWorked:(\d+)', nuxt) or [None, '0'])[1])
    result['member_since'] = (re.search(r'memberSince:"([^"]+)"', nuxt) or [None, None])[1]
    result['last_worked'] = (re.search(r'lastWorkedOn:"([^"]+)"', nuxt) or [None, None])[1]
    result['response_state'] = (re.search(r'responsiveState:"([^"]+)"', nuxt) or [None, None])[1]

    # Portfolio titles
    result['portfolio_titles'] = re.findall(r'"([^"]{10,80})"(?=,\{.*?\})', nuxt)

    return result
```

### 3. Work history job titles (regex from NUXT args)

Job titles appear as string literals in the NUXT function call arguments near the end:

```python
# Find the closing arguments block of the NUXT function call
args_block = nuxt_script[nuxt_script.rfind('}('):]
job_titles = re.findall(r'"([A-Z][^"]{15,100})"', args_block)
```

---

## HTML DOM Notes (visible elements)

The page is a client-rendered Vue app. Most DOM elements are **not useful for static HTML parsing** because they contain Vue component placeholders. However, the following are SSR-rendered and available in static HTML:

| Element | CSS / attribute selector | Contains |
|---|---|---|
| Page `<title>` | `title` | `"Name - Title - Upwork Freelancer from City, Country"` |
| All `<meta>` tags | `head meta` | Key fields (see Source 1 table) |
| Job Success badge text | `span[data-test="badge-hidden-label"]` next sibling | `"Job Success"` label |
| Top Rated badge text | `span` containing `"Top Rated"` text | `"Top Rated"` or `"Top Rated Plus"` |
| JSS percentage | `span` before `data-test="badge-hidden-label"` | `"100%"` |
| `data-qa="top-nav-visitor-ia"` | nav element | Navigation (not profile data) |

> **Note:** For production parsing, always use `window.__NUXT__` or meta tags. DOM selectors for profile data are fragile as they rely on Vue SSR output that may change.
