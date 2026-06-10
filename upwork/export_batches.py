"""Export deduplicated profiles into batch files for LLM analysis.

Deduplicates by uid (or name if uid is null), sorts by our_tier
(established -> emerging -> minimal), splits into files of ~23 profiles.

Output: upwork/batch_01.md ... batch_04.md
"""
import json
import math
import sqlite3

DB = "upwork/upwork_parsed.db"
OUT_DIR = "upwork"
BATCH_SIZE = 23

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

rows = con.execute("""
SELECT
  id, uid, name, our_tier,
  title, overview, skills,
  total_jobs, total_hours, nss_score,
  hourly_rate, country,
  work_history_titles,
  ROUND(
    total_hours / MAX(
      (julianday('now') - julianday(member_since)) / 30.44,
      1
    ), 1
  ) AS hrs_per_month
FROM profiles
WHERE name IS NOT NULL AND name != ''
  AND our_tier IS NOT NULL
ORDER BY CASE our_tier
           WHEN 'established' THEN 1
           WHEN 'emerging'    THEN 2
           ELSE 3 END,
         hrs_per_month DESC
""").fetchall()

# Deduplicate: keep first occurrence per uid (or per name if uid is null)
seen = set()
unique = []
dupes = []
for r in rows:
    key = r["uid"] if r["uid"] else r["name"]
    if key not in seen:
        seen.add(key)
        unique.append(r)
    else:
        dupes.append((r["id"], r["name"], key))

print(f"Total rows: {len(rows)}, unique profiles: {len(unique)}, duplicates skipped: {len(dupes)}")
if dupes:
    print("Duplicates:")
    for row_id, name, key in dupes:
        print(f"  id={row_id}  {name}  (key={key})")


def fmt_jss(val):
    if val is None:
        return "N/A"
    pct = int(round(val * 100)) if val <= 1 else int(val)
    return f"{pct}%"


def fmt_profile(idx, r):
    lines = []
    lines.append(f"===== PROFILE {idx} =====")

    tier = r["our_tier"] or "unknown"
    jobs = r["total_jobs"] or 0
    hours = int(r["total_hours"]) if r["total_hours"] else 0
    jss = fmt_jss(r["nss_score"])
    lines.append(f"TIER: {tier} | jobs {jobs} | hours {hours} | JSS {jss}")
    lines.append("")

    lines.append(f"TITLE: {r['title'] or '(none)'}")
    lines.append("")

    overview = r["overview"] or "(none)"
    lines.append(f"OVERVIEW:\n{overview}")
    lines.append("")

    # Skills
    skills_raw = r["skills"]
    if skills_raw:
        try:
            skill_list = json.loads(skills_raw)
            if isinstance(skill_list, list):
                names = []
                for s in skill_list:
                    if isinstance(s, str):
                        names.append(s)
                    elif isinstance(s, dict):
                        names.append(s.get("prettyName") or s.get("name") or s.get("prefLabel") or s.get("skill") or str(s))
                skills_str = ", ".join(names)
            else:
                skills_str = str(skill_list)
        except (json.JSONDecodeError, TypeError):
            skills_str = skills_raw
    else:
        skills_str = "(none)"
    lines.append(f"SKILLS: {skills_str}")
    lines.append("")

    # Work history / feedback
    wh_raw = r["work_history_titles"]
    lines.append("WORK HISTORY (client feedback):")
    if wh_raw:
        try:
            wh = json.loads(wh_raw)
            if isinstance(wh, list):
                for item in wh[:10]:
                    if isinstance(item, dict):
                        title = item.get("title", "")
                        feedback = item.get("feedback", "")
                        lines.append(f'- {title} — "{feedback}"')
                    elif isinstance(item, str):
                        lines.append(f"- {item}")
            else:
                lines.append(f"- {wh}")
        except (json.JSONDecodeError, TypeError):
            lines.append(f"- {wh_raw}")
    else:
        lines.append("- (none)")

    return "\n".join(lines)


# Group by tier, then split each tier into batches (no mixing)
from collections import OrderedDict

tier_groups = OrderedDict()
for r in unique:
    t = r["our_tier"]
    tier_groups.setdefault(t, []).append(r)

all_batches = []
for tier, profiles in tier_groups.items():
    num = math.ceil(len(profiles) / BATCH_SIZE)
    for b in range(num):
        start = b * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(profiles))
        all_batches.append(profiles[start:end])

print(f"Writing {len(all_batches)} batch files (no tier mixing, ~{BATCH_SIZE} each)")

for b, batch in enumerate(all_batches):
    parts = []
    for i, r in enumerate(batch, start=1):
        parts.append(fmt_profile(i, r))

    filename = f"{OUT_DIR}/batch_{b+1:02d}.md"
    with open(filename, "w") as f:
        f.write("\n\n".join(parts) + "\n")

    tier_counts = {}
    for r in batch:
        t = r["our_tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    print(f"  {filename}: {len(batch)} profiles {dict(tier_counts)}")

con.close()
