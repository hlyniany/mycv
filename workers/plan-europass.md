# Plan: Europass

> Back to [overview](plan-overview.md) · Phase: [7](plan-phases.md) · Related: [open-questions #2](plan-open-questions.md)

**Platform**: https://europass.europa.eu/
**Status**: Need to research API/MCP availability (see [open-questions #2](plan-open-questions.md))

---

## 4.1 READ: From Europass - `scripts/read_europass.sh <xml_file> <domain>`
- **Input**: Europass CV XML (manually exported from platform), target domain
- **Tool**: Python + XML parsing (lxml or xml.etree)
- **Output**: Diff file in review/europass-{domain}-{timestamp}.diff
- **Process**:
  1. Parse Europass XML schema
  2. Map to JSONResume:
     - PersonName → basics.name
     - ContactInfo → basics.email, basics.phone, basics.location
     - WorkExperience → work[]
     - Education → education[]
     - Skills → skills[], languages[]
  3. Compare against data/{domain}.json
  4. Generate diff
- **Limitation**: Manual export from Europass.europa.eu required (no automated API access)

## 4.2 WRITE: To Europass XML - `scripts/write_europass.sh <domain>`
- **Input**: data/{domain}.json
- **Tool**: Python + Jinja2 XML template
- **Output**: europass-{domain}.xml
- **Template**: templates/europass.xml.j2
- **Process**:
  1. Load domain JSON
  2. Map JSONResume → Europass XML structure
  3. Render Jinja2 template
  4. Validate XML against Europass schema
  5. Save XML file
  6. User manually imports to Europass platform
  7. Platform generates official Europass PDF

**Europass XML sections**:
```xml
<europass>
  <learnerinfo>
    <identification> (name, contact)
    <workexperience>
    <education>
    <skills> (languages, technical, communication)
    <achievements> (certifications, awards)
  </learnerinfo>
</europass>
```
