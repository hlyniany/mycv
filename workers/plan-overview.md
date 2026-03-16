# Plan: CV ETL Research - Overview

> See also: [phases](plan-phases.md) · [html](plan-html.md) · [linkedin](plan-linkedin.md) · [orcid](plan-orcid.md) · [europass](plan-europass.md) · [json-internal](plan-json-internal.md) · [files](plan-files.md) · [open-questions](plan-open-questions.md) · [verification](plan-verification.md)

## TL;DR
Build CV ETL with **4 separate JSONResume files** (it.json, psychology.json, theatre.json, bank_marketing.json). Shell scripts for reading/writing data from HTML/LinkedIn/ORCID/Europass. Manual diff review workflow with git-native source control and detailed changelog. No automation beyond existing GitHub Pages deployment. No PDF generation (manual browser "Save as PDF").

---

## Decisions

**Architecture**:
- ✅ **4 separate JSON files** (not one master with filtering)
   - Simpler for manual editing and review
   - Clear domain separation
   - Easier git diffs
- ✅ **Shell scripts** (not Python CLI or GitHub Actions automation)
   - User runs scripts manually when needed
   - Full control over when data syncs
   - Transparent operation
- ✅ **Git-native workflow** (manual commits after review)
   - User reviews diffs before committing
   - Detailed changelogs track all changes
   - Version history in git log
- ✅ **No PDF generation** (browser "Save as PDF")
   - Simplify tooling
   - Browser PDF rendering is sufficient
   - Avoid Weasyprint/Puppeteer dependencies

**Data Sources**:
- ✅ LinkedIn: Official export only (manual download)
- ✅ ORCID: API read/write with OAuth 2.0
- ⚠️ Europass: Manual XML export/import (API TBD - see [open-questions](plan-open-questions.md) #2)
- ✅ HTML: BeautifulSoup parsing + Jinja2 generation

**Excluded**:
- ❌ Automated scheduling (cron, GitHub Actions triggers)
- ❌ LinkedIn API/scraping (not viable)
- ❌ PDF generation tooling (manual from browser)
- ❌ Single master JSON with filtering (too complex for manual editing)
- ❌ Automated git commits (user must review and commit manually)
