# Plan: Internal JSON File (Source of Truth)

> Back to [overview](plan-overview.md) · Phase: [5](plan-phases.md)

**File**: data/cv.resume.json (single master file)
**Schema**: JSONResume v1.0.0 + custom fields

### Domain Tagging Convention
Each entry in `work[]`, `education[]`, `skills[]`, etc. carries:
- `"domains": ["it", "psychology", ...]` — which domain pages/exports include this entry
- `"noorcid": true` — exclude from ORCID export (optional flag)

Example:
```json
{
  "work": [{
    "company": "EPAM Systems",
    "position": "Software Engineer",
    "domains": ["it"],
    "noorcid": false
  }, {
    "company": "City Theatre",
    "position": "Stage Manager",
    "domains": ["theatre", "psychology"]
  }]
}
```

---

## 5.1 IMPORT: Receive updates from sources - `scripts/import_to_json.sh <source> <diff_file>`
- **Input**: Diff file from read_*.sh scripts (HTML, LinkedIn, ORCID, Europass)
- **Tool**: Python + JSON merge
- **Output**: Updated data/cv.resume.json (if user approves)
- **Process**:
  1. Load diff file from review/ folder
  2. Display structured diff:
     ```
     ADDED:
     + work[5]: Flying Donkey IT (2021-2023)
     + skills[12]: Zapier
     
     MODIFIED:
     ~ work[2].endDate: 2022-12-31 → 2022-08-31
     ~ education[0].gpa: 3.8 → 3.9
     
     REMOVED:
     - work[8]: (temporary position)
     ```
  3. Ask user: "Apply changes? [y/n/e(dit)]"
  4. If yes: Apply changes to data/cv.resume.json
  5. If edit: Open in $EDITOR for manual adjustments
  6. User adds/adjusts `"domains"` tags on new entries
  7. Generate changelog entry
  8. Git add data/cv.resume.json
  9. Print: "Ready to commit. Review with `git diff --cached` then `git commit`"

## 5.2 DIFF: Generate for manual review - `scripts/generate_diff.sh`
- **Input**: data/cv.resume.json (working tree vs. git HEAD)
- **Tool**: Python JSON diff or git diff
- **Output**: Human-readable diff display
- **Process**:
  1. Compare current JSON vs. last committed version
  2. Parse JSON-level changes (not just text diff)
  3. Display semantic diff:
     ```
     Changed in cv.resume.json since last commit:
     
     Section: Work Experience
     - Modified: EPAM Systems end date
       Before: 2022-08-31
       After: 2022-08-15
     
     Section: Skills
     - Added: GitHub Actions (advanced)
     - Removed: Jenkins (intermediate)
     ```
  4. Exit code: 0 if changes, 1 if no changes

## 5.3 UPDATE: Apply with git - `scripts/apply_update.sh`
- **Input**: Modified data/cv.resume.json (user has manually edited)
- **Tool**: Git commands
- **Output**: Staged changes (not committed yet)
- **Process**:
  1. Validate JSON syntax
  2. Validate JSONResume schema compliance
  3. Generate changelog entry (see 5.4)
  4. Git add data/cv.resume.json
  5. Append to CHANGELOG.md
  6. Git add CHANGELOG.md
  7. Print suggested commit message:
     ```
     Update IT domain: LinkedIn import 2026-03-16
     
     - Added: New work experience (Flying Donkey IT)
     - Updated: EPAM end date correction
     See CHANGELOG.md for details
     ```
  8. User runs: `git commit` (manual step for final review)

## 5.4 CHANGELOG: Detailed format - `CHANGELOG.md`

**Structure**:
```markdown
# Changelog - cv.resume.json

All notable changes to the master resume will be documented here.
Format: [ISO Date] - Source - Summary

---

## [2026-03-16] - LinkedIn Import

**Source**: LinkedIn data export (Archive-2026-03-16.zip)
**Script**: scripts/read_linkedin.sh
**Applied by**: Manual review

### Added
- **Work Experience #5**: Flying Donkey IT
  - Position: API integration engineer
  - Dates: 2021-08-01 to 2023-12-31
  - Location: Kyiv, Ukraine
  - Highlights: 3 items (SaaS integration, no-code tools, AI APIs)
  - JSON path: work[5]

- **Skills**: Zapier, Make, Appsmith
  - JSON path: skills[12-14]

### Changed
- **Work Experience #2**: EPAM Systems end date
  - Field: work[2].endDate
  - Before: 2022-12-31
  - After: 2022-08-31
  - Reason: Corrected based on LinkedIn records

### Removed
- None

### Manual Edits
- Excluded military service details (tagged `"domains": ["psychology"]` only)
- Consolidated similar skill entries (Node.js, NodeJS → Node.js)

---

## [2026-03-10] - ORCID Sync

**Source**: ORCID API read
**Script**: scripts/read_orcid.sh
**Applied by**: Partial - publications only

### Added
- **Publications #1**: "Microservices Architecture Patterns"
  - Type: Conference paper
  - DOI: 10.1234/example
  - JSON path: publications[0]

### Changed
- None

### Removed
- None

### Manual Edits
- Skipped adding peer-review activities (not relevant for IT resume)

---
```

**Script**: `scripts/changelog_entry.sh <domain> <source> <summary>`
- Auto-generates changelog section from git diff
- Opens in $EDITOR for user refinement
- Appends to CHANGELOG-{domain}.md
- User can edit "Manual Edits" section
