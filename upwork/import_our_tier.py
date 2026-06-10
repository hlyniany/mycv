"""Import our_tier values from upwork/our_tier.txt into the profiles table.

Expected format of our_tier.txt (space-aligned table with -> separator):
    id  name           old_tier   -> our_tier     dup
    ----------------------------------------------------
       1  Sergii C.      top_rated  -> emerging
       2  Borys G.       top_rated  -> established
"""
import re
import sqlite3

DB = "upwork/upwork_parsed.db"
TXT = "upwork/our_tier.txt"

con = sqlite3.connect(DB)

# Ensure column exists
cols = [r[1] for r in con.execute("PRAGMA table_info(profiles)").fetchall()]
if "our_tier" not in cols:
    con.execute("ALTER TABLE profiles ADD COLUMN our_tier TEXT")
    print("Added our_tier column")

# Read file and update
with open(TXT) as f:
    lines = [l.rstrip() for l in f]

updated = 0
for line in lines:
    # Match lines like: "   1  Sergii C.      top_rated  -> emerging"
    m = re.match(r'\s*(\d+)\s+.+?->\s+(\S+)', line)
    if m:
        row_id = int(m.group(1))
        tier = m.group(2)
        con.execute("UPDATE profiles SET our_tier = ? WHERE id = ?", (tier, row_id))
        updated += 1

con.commit()
con.close()
print(f"Updated {updated} rows from {len(lines)} lines")
