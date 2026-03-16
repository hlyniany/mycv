# Plan: Implementation Phases

> Back to [overview](plan-overview.md)

## Phase 1: Repository Setup (*independent*)
1. Create folder structure:
   ```
   mycv/
   ├── data/
   │   ├── it.json (empty JSONResume structure)
   │   ├── psychology.json
   │   ├── theatre.json
   │   └── bank_marketing.json
   ├── review/ (for diffs)
   ├── scripts/
   ├── templates/
   │   ├── cv.html.j2
   │   └── europass.xml.j2
   ├── CHANGELOG-it.md
   ├── CHANGELOG-psychology.md
   ├── CHANGELOG-theatre.md
   ├── CHANGELOG-bank_marketing.md
   ├── .gitignore (add .env, review/*, tokens)
   └── requirements.txt
   ```

2. Initialize 4 JSONResume files with basic structure:
   ```json
   {
     "basics": {"name": "Vitaliy Hlynianyi-Zhuk", "email": "...", "phone": "..."},
     "work": [],
     "education": [],
     "skills": [],
     "meta": {"version": "1.0.0", "lastModified": "2026-03-16"}
   }
   ```

3. Git commit initial structure

## Phase 2: HTML Data Import (*depends on Phase 1*)
> Details: [plan-html.md](plan-html.md)

1. Implement `scripts/read_html_initial.sh`
2. Run on VitaliyHlynianyiZhuk2025.html
3. Extract all experience, education, skills to temp JSON
4. **Manual step**: User distributes data across 4 domain JSONs
5. Git commit each domain file separately with message: "Initial import from HTML"

## Phase 3: LinkedIn Import (*parallel with Phase 2*)
> Details: [plan-linkedin.md](plan-linkedin.md)

1. User requests LinkedIn export (Settings > Data Privacy > Get copy)
2. Wait 24 hours for ZIP file
3. Implement `scripts/read_linkedin.sh`
4. Run script on export ZIP for each domain
5. Review diffs in review/ folder
6. User decides which data to merge into which domain files
7. Git commit changes

## Phase 4: HTML Generation (*depends on Phase 2*)
> Details: [plan-html.md](plan-html.md)

1. Create templates/cv.html.j2 (Jinja2 HTML template)
   - Based on existing VitaliyHlynianyiZhuk2025.html structure
   - Add Jinja2 variables: `{{ basics.name }}`, `{% raw %}{% for job in work %}{% endraw %}`, etc.
2. Implement `scripts/write_html_full.sh`
3. Generate HTML for all 4 domains:
   ```bash
   ./scripts/write_html_full.sh it
   ./scripts/write_html_full.sh psychology
   ./scripts/write_html_full.sh theatre
   ./scripts/write_html_full.sh bank_marketing
   ```
4. Test in browser (open locally)
5. Git commit HTML files
6. Push to GitHub (existing gh-pages action will deploy)

## Phase 5: Diff & Changelog Tools (*parallel with Phase 4*)
> Details: [plan-json-internal.md](plan-json-internal.md)

1. Implement `scripts/generate_diff.sh` (JSON semantic diff)
2. Implement `scripts/import_to_json.sh` (apply diffs with review)
3. Implement `scripts/apply_update.sh` (stage changes, prepare commit)
4. Implement `scripts/changelog_entry.sh` (auto-generate changelog)
5. Test full workflow:
   - Make manual edit to data/it.json
   - Run generate_diff.sh → see changes
   - Run apply_update.sh → stage and prepare commit
   - Review git diff --cached
   - Git commit
6. Verify CHANGELOG-it.md updated correctly

## Phase 6: ORCID Integration (*depends on Phase 5*)
> Details: [plan-orcid.md](plan-orcid.md)

1. Register ORCID Sandbox app at https://sandbox.orcid.org/developer-tools
2. Implement `scripts/orcid_oauth.sh` (OAuth consent flow, save token to .env)
3. Test OAuth flow in sandbox
4. Implement `scripts/read_orcid.sh`
5. Test read from sandbox ORCID
6. Implement `scripts/write_orcid.sh`
7. Test write to sandbox (create test employment record)
8. Verify in sandbox ORCID web interface
9. Switch to production ORCID (get production credentials)
10. Test production read
11. Test production write (one domain, e.g., IT)

## Phase 7: Europass Integration (*parallel with Phase 6*)
> Details: [plan-europass.md](plan-europass.md)

1. **Research step**: Investigate Europass API/MCP availability (see [open-questions](plan-open-questions.md) #2)
2. If no API: Use manual XML export/import approach
3. Create templates/europass.xml.j2 (Europass XML schema template)
4. Implement `scripts/write_europass.sh` (JSONResume → Europass XML)
5. Generate Europass XML for one domain (IT)
6. Manually import to https://europass.europa.eu
7. Verify import successful, data correct
8. If needs adjustments: refine XML template
9. Implement `scripts/read_europass.sh` (Europass XML → JSONResume diff) - optional
10. Document manual workflow in README

## Phase 8: Full Workflow Testing (*depends on all phases*)

1. **Test scenario 1**: LinkedIn update cycle
   - Export LinkedIn data → Import to JSON → Review diff → Apply → Commit → Generate HTML → Push to GitHub
2. **Test scenario 2**: ORCID round-trip
   - Read from ORCID → Review diff → Modify local JSON → Write back to ORCID → Read again to verify
3. **Test scenario 3**: Manual JSON edit
   - Edit data/it.json directly → Generate diff → Apply → Commit → Update HTML + ORCID + Europass
4. **Test scenario 4**: Data consistency
   - Verify all 4 domains maintain proper JSONResume schema
   - No data corruption across read/write cycles
5. Git tag: `v1.0.0-complete-workflow`

---

## Phase Dependency Graph

```
Phase 1 (Setup)
  ├── Phase 2 (HTML Import)
  │     └── Phase 4 (HTML Generation) ──┐
  ├── Phase 3 (LinkedIn Import)         │
  └───────────────── Phase 5 (Diff Tools) ──parallel with Phase 4
                       ├── Phase 6 (ORCID)
                       └── Phase 7 (Europass) ──parallel with Phase 6
                              └── Phase 8 (Full Testing) ──depends on all
```
