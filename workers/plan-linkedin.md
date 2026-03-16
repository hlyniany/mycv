# Plan: LinkedIn

> Back to [overview](plan-overview.md) · Phase: [3](plan-phases.md) · Related: [open-questions #1](plan-open-questions.md)

**Data source**: Manual export (Settings & Privacy > Data Privacy > Get a copy of your data)
**Destination model**: Separate LinkedIn account per domain. Each account gets its own filtered export from the master JSON.

---

## 2.1 READ: From manual download - `scripts/read_linkedin.sh <export_zip> <domain>`
- **Input**: LinkedIn export ZIP file (contains CSV/JSON), target domain name
- **Tool**: Python + CSV/JSON parsing
- **Output**: Diff file in review/linkedin-{domain}-{timestamp}.diff
- **Process**:
  1. Extract ZIP: Profile.csv, Positions.csv, Education.csv, Skills.csv, Certifications.csv
  2. Parse CSV to JSONResume format
  3. Compare against data/cv.resume.json (filtered to entries tagged with target domain)
  4. Generate human-readable diff
  5. Save diff to review/ folder
  6. User manually reviews and applies changes to master JSON

**LinkedIn Export contains**:
- Profile.csv - Name, headline, contact info
- Positions.csv - Company, title, dates, description
- Education.csv - School, degree, field, dates
- Skills.csv - Skill names, endorsements count
- Certifications.csv - Name, authority, dates

## 2.2 WRITE: Update LinkedIn - **NOT AVAILABLE**
- **LinkedIn API**: ❌ No write access to personal profile
- **MCP tool**: Need to research (see [open-questions #1](plan-open-questions.md))
- **Recommendation**: Manual update only
- User manually updates LinkedIn profile from internal JSON
