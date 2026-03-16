# Plan: CV ETL Research - Overview

> See also: [phases](plan-phases.md) · [html](plan-html.md) · [linkedin](plan-linkedin.md) · [orcid](plan-orcid.md) · [europass](plan-europass.md) · [json-internal](plan-json-internal.md) · [files](plan-files.md) · [open-questions](plan-open-questions.md) · [verification](plan-verification.md)

## TL;DR
Build CV ETL with **one master JSONResume file** (`data/cv.json`) where each entry has domain tags (e.g. `"domains": ["it", "psychology"]`). Cross-domain activities are stored once with multiple tags. Shell scripts filter by domain when exporting to destinations. Manual diff review workflow with git-native source control and detailed changelog. No automation beyond existing GitHub Pages deployment. No PDF generation (manual browser "Save as PDF").

---

## Decisions

**Architecture**:
- ✅ **1 master JSON file** with domain tags per entry
   - Cross-domain activities stored once (no duplication)
   - Tags like `"domains": ["it", "theatre"]` control which exports include each entry
   - Export scripts filter by domain
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

**Destinations** (each filters master JSON differently):
- ✅ **HTML/GitHub Pages**: Separate page per domain, index.html links to each
- ✅ **LinkedIn**: Separate account per domain → separate filtered JSON export per domain
- ✅ **ORCID**: All domains together (single profile), entries tagged `-noorcid` are excluded
- ⚠️ **Europass**: Not defined yet, low priority

**Excluded**:
- ❌ Automated scheduling (cron, GitHub Actions triggers)
- ❌ LinkedIn API/scraping (not viable)
- ❌ PDF generation tooling (manual from browser)
- ❌ Automated git commits (user must review and commit manually)
