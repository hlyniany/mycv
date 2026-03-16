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
- data/cv.json - Single master resume (all domains, tagged per entry)

### Scripts (shell + Python)
- scripts/read_html_initial.sh (HTML → JSON, one-time)
- scripts/read_html_structured.sh (HTML → JSON, recovery)
- scripts/read_linkedin.sh (LinkedIn ZIP → diff)
- scripts/read_orcid.sh (ORCID API → diff)
- scripts/write_html_full.sh (JSON → HTML per domain + index)
- scripts/write_html_update.sh (JSON → HTML partial)
- scripts/write_orcid.sh (JSON → ORCID API, excludes -noorcid)
- scripts/generate_diff.sh (show JSON changes)
- scripts/import_to_json.sh (apply diff to JSON)
- scripts/apply_update.sh (stage git commits)
- scripts/changelog_entry.sh (generate changelog)
- scripts/orcid_oauth.sh (OAuth consent flow)

*Europass scripts deferred (low priority)*

### Templates
- templates/cv.html.j2 - HTML resume template (per-domain page)
- templates/index.html.j2 - Landing page with links to each domain

*Europass template deferred*

### Changelogs
- CHANGELOG.md (single file for master JSON)

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
python-dotenv>=1.0.0      # .env file handling
```
