# Plan: Files Inventory

> Back to [overview](plan-overview.md)

---

## Existing Files
- [index.html](../index.html) - Redirect to main CV
- [VitaliyHlynianyiZhuk2025.html](../VitaliyHlynianyiZhuk2025.html) - Current HTML CV (data source)
- [workers/](.) - Plan documents
- [README.md](../README.md) - Documentation

## To Create

### Data (source of truth)
- data/it.json - IT domain resume
- data/psychology.json - Psychology domain resume
- data/theatre.json - Theatre domain resume
- data/bank_marketing.json - Bank marketing domain resume

### Scripts (shell + Python)
- scripts/read_html_initial.sh (HTML → JSON, one-time)
- scripts/read_html_structured.sh (HTML → JSON, recovery)
- scripts/read_linkedin.sh (LinkedIn ZIP → diff)
- scripts/read_orcid.sh (ORCID API → diff)
- scripts/read_europass.sh (Europass XML → diff)
- scripts/write_html_full.sh (JSON → HTML)
- scripts/write_html_update.sh (JSON → HTML partial)
- scripts/write_orcid.sh (JSON → ORCID API)
- scripts/write_europass.sh (JSON → Europass XML)
- scripts/generate_diff.sh (show JSON changes)
- scripts/import_to_json.sh (apply diff to JSON)
- scripts/apply_update.sh (stage git commits)
- scripts/changelog_entry.sh (generate changelog)
- scripts/orcid_oauth.sh (OAuth consent flow)

### Templates
- templates/cv.html.j2 - HTML resume template
- templates/europass.xml.j2 - Europass XML template

### Changelogs
- CHANGELOG-it.md
- CHANGELOG-psychology.md
- CHANGELOG-theatre.md
- CHANGELOG-bank_marketing.md

### Config
- .env (ORCID client ID, secret, tokens) - gitignored
- .gitignore (add: .env, review/*, tokens, temp files)
- requirements.txt (Python dependencies)

## Python Dependencies (requirements.txt)
```
beautifulsoup4>=4.12.0    # HTML parsing
jinja2>=3.1.0             # Templating
jsonschema>=4.17.0        # JSONResume validation
requests>=2.31.0          # ORCID API calls
lxml>=4.9.0               # XML parsing (Europass)
python-dotenv>=1.0.0      # .env file handling
```
