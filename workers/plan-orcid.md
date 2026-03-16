# Plan: ORCID

> Back to [overview](plan-overview.md) · Phase: [6](plan-phases.md) · Related: [open-questions #3](plan-open-questions.md)

**API**: https://api.orcid.org/v3.0/{orcid_id}
**User status**: Has existing ORCID account ✅

---

## 3.1 READ: From ORCID API - `scripts/read_orcid.sh <domain>`
- **Input**: ORCID ID, OAuth token, target domain
- **Tool**: Python + requests library
- **Output**: Diff file in review/orcid-{domain}-{timestamp}.diff
- **Process**:
  1. OAuth 2.0 authentication (credentials in .env file)
  2. GET /{orcid_id}/activities (employment, education, works, fundings)
  3. GET /{orcid_id}/person (name, biography, external identifiers)
  4. Parse ORCID XML/JSON → JSONResume format
  5. Compare against data/{domain}.json
  6. Generate diff for manual review
- **First run**: Need OAuth consent flow (browser popup)

**ORCID data structure**:
```
/activities
  /employments - Job history
  /educations - Academic credentials
  /works - Publications, presentations
  /fundings - Grants
  /peer-reviews - Review activity
/person
  /name, /biography, /addresses
  /external-identifiers
```

## 3.2 WRITE: To ORCID API - `scripts/write_orcid.sh <domain>`
- **Input**: data/{domain}.json, OAuth token
- **Tool**: Python + requests library
- **Output**: ORCID profile updated
- **Process**:
  1. Load domain JSON file
  2. Map JSONResume → ORCID sections:
     - work[] → POST /{orcid_id}/employments
     - education[] → POST /{orcid_id}/educations  
     - publications[] → POST /{orcid_id}/works (if present)
  3. Set visibility per item (public/limited/private)
  4. POST/PUT to ORCID API
  5. Log changes to changelog
- **Credentials**: OAuth token required (one-time browser consent flow)

## OAuth Setup (one-time)
1. Register app at https://orcid.org/developer-tools
2. Get client ID + secret
3. Run `scripts/orcid_oauth.sh` for browser consent flow
4. Save refresh token to .env file
