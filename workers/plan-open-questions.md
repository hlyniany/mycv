# Plan: Open Questions & Further Considerations

> Back to [overview](plan-overview.md)

---

## 1. LinkedIn MCP Tool - Need Research
**Question**: Does LinkedIn MCP server exist for profile updates?
**Action**: Search for MCP tools related to LinkedIn
**Options**:
  - A. MCP tool exists → Update plan to use it for LinkedIn write
  - B. No MCP tool → Confirm manual-only approach
**Impact**: If MCP available, add `scripts/write_linkedin_mcp.sh`

## 2. Europass API/MCP - Need Research
**Question**: Is there Europass API or MCP server?
**Action**: Research European Commission APIs, search for Europass MCP
**Options**:
  - A. Europass API exists → Use API for read/write
  - B. Europass MCP exists → Use MCP tool
  - C. Manual only → Keep XML export/import approach
**Impact**: If API/MCP available, simplify Europass integration

## 3. ORCID OAuth Token Storage
**Question**: How to securely store OAuth refresh token?
**Options**:
  - A. .env file (gitignored) - simple, local only
  - B. System keyring (keyring Python library) - more secure
  - C. OS environment variables - persistent across reboots
**Recommendation**: Start with .env, upgrade to keyring if needed
**Security**: Never commit tokens to git

## 4. JSONResume Schema Validation
**Question**: Strict validation or allow custom fields?
**Recommendation**: 
  - Validate required JSONResume fields
  - Allow custom fields (additionalProperties: true)
  - Useful for domain-specific metadata
**Example custom fields**:
  ```json
  {
    "work": [{
      "company": "...",
      "domain_relevance": 0.95,
      "tags": ["IT", "integration"],
      "visibility_notes": "Highlight for IT roles"
    }]
  }
  ```

## 5. Diff Format Preferences
**Question**: JSON diff format - how detailed?
**Options**:
  - A. High-level: Section changes only (work, education, skills)
  - B. Field-level: Show each field change
  - C. Line-level: Traditional git diff format
**Recommendation**: Field-level (option B) - balance detail vs. readability

## 6. Error Handling
**Question**: What if API calls fail (ORCID, network issues)?
**Requirements**:
  - Retry logic with exponential backoff
  - Clear error messages
  - Partial success handling (some items updated, others failed)
  - Log errors to scripts.log

## 7. Multiple Devices Workflow
**Question**: How to work across devices (laptop, desktop)?
**Recommendation**:
  - Use git as sync mechanism
  - Git pull before running scripts
  - Git push after commits
  - Conflict resolution: Manual merge required

## 8. Backup Strategy
**Question**: How to protect against data loss?
**Recommendation**:
  - Git history provides versioning
  - GitHub remote as backup
  - Optional: Periodic git tag releases (v1.0.0, v1.1.0)
  - Optional: Export all domains to single archive: `scripts/backup_all.sh`
