# CV Project — Cowork Session Guide

## Golden Source Rule
`data/cv.resume.json` is the single source of truth (JSON Resume schema).
Every change must be applied to **both** files simultaneously:
1. `data/cv.resume.json`
2. `docs/VitaliyHlynianyiZhuk2025.html`

## File Map

| File | Role |
|------|------|
| `data/cv.resume.json` | Golden source — JSON Resume standard (`$schema: jsonresume/resume-schema/master`) |
| `docs/VitaliyHlynianyiZhuk2025.html` | Primary rendered CV — inline styles, no external CSS |
| `manual/resume.json` | LinkedIn export — reference only, do not edit |
| `manual/Profile.pdf` | LinkedIn PDF export — reference only |
| `review/cv.resume.json` | Older review copy — do not use as source |
| `tools/profile-studio/` | Vue.js JSON Resume editor — separate tool |
| `server.py` | Local dev server |

## Connected Systems (this session)

- **Make.com MCP** — team ID `114422` (Flying Donkey org). Other orgs (RACQ Solar, GEM, Murray Conservatorium, sandbox) require separate API keys per team.
- **GitHub** — repo: `hlyniany/mycv`, published at `hlyniany.github.io/mycv/`

## Related Project Folders (read for context only)

| Path | Project |
|------|---------|
| `/Users/vitaliy/Documents/GitHub/missive-crm-add-on/` | Epic Flooring CRM add-on |
| `/Users/vitaliy/Documents/GitHub/bash/homeassistant/` | Home Assistant Green |
| `/Users/vitaliy/Documents/GitHub/vtt/` | Voice-to-Text Android app |
| `/Users/vitaliy/Documents/tg-standalone-az/` | Telegram MCP Server on Azure |
| `/Users/vitaliy/Documents/GitHub/amm-ocr-poc/` | OCR POC (empty README — described verbally) |
| `/Users/vitaliy/Documents/GitHub/hujuskalo/` | Real Estate Classifieds Scraper |

## HTML Structure Notes

- Section order: EXPERIENCE → PROJECTS → EDUCATION → LANGUAGES → CERTIFICATIONS → HOBBIES → RECOMMENDATIONS
- Layout: two-column flex (`100px label | 1px divider | flex:1 content`)
- Each work entry: `h3` company+location, italic date (right), italic position, `ul` highlights

## JSON Resume Sections in Use

`basics`, `work`, `projects`, `volunteer`, `education`, `certificates`, `skills`, `languages`, `interests`, `references`

Not used: `awards`, `publications`
