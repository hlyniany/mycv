# Plan: Verification & Next Steps

> Back to [overview](plan-overview.md)

---

## Verification Criteria

1. **Data Integrity**: Master cv.resume.json validates against JSONResume schema (with custom domain fields)
2. **Domain Filtering**: Each domain export contains only entries tagged for that domain
3. **Cross-domain Entries**: Entries tagged with multiple domains appear in all relevant exports
4. **Round-trip Accuracy**: Data survives HTML → JSON → HTML conversion without loss
5. **ORCID Sync**: Data written to ORCID matches local JSON (minus `-noorcid` entries), reads back correctly
6. **Diff Accuracy**: Diff tools correctly identify added/changed/removed items
7. **Git History**: Changelog matches git commit history, no undocumented changes
8. **Manual Review**: User can understand all diffs without confusion

---

## Next Steps After Plan Approval

### 1. Confirm Further Considerations
- Research LinkedIn MCP ([open-questions #1](plan-open-questions.md))
- Research Europass API/MCP ([open-questions #2](plan-open-questions.md))
- Decide OAuth storage method ([open-questions #3](plan-open-questions.md))
- Confirm diff format preference ([open-questions #5](plan-open-questions.md))

### 2. Phase 1 Implementation
- Create folder structure
- Initialize master cv.resume.json with domain tag convention
- Set up .gitignore
- Initial git commit

### 3. Phase 2 Development
- Implement scripts/read_html_initial.sh
- Extract data from VitaliyHlynianyiZhuk2025.html
- Add domain tags to each entry (manual)
- First data commits

### 4. Iterate Through Phases 3-8
See [plan-phases.md](plan-phases.md) for full sequencing and dependencies.
