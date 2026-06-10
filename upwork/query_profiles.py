import sqlite3

con = sqlite3.connect("upwork/upwork_parsed.db")
cur = con.execute("""
SELECT
  id,
  name,
  COALESCE(top_rated_status, 'none') AS tier,
  nss_score                          AS jss,
  total_earnings,
  total_jobs,
  total_hours,
  hourly_rate,
  country,
  member_since,
  ROUND(
    total_hours / MAX(
      (julianday('now') - julianday(member_since)) / 30.44,
      1
    ), 1
  ) AS hrs_per_month
FROM profiles
WHERE name IS NOT NULL AND name != ''
ORDER BY CASE COALESCE(top_rated_status,'none')
           WHEN 'hipo'      THEN 1
           WHEN 'top_rated' THEN 2
           ELSE 3 END,
         nss_score DESC
""")

rows = cur.fetchall()
headers = [d[0] for d in cur.description]

widths = [len(h) for h in headers]
str_rows = []
for row in rows:
    str_row = [str(v) if v is not None else "" for v in row]
    str_rows.append(str_row)
    for i, v in enumerate(str_row):
        widths[i] = max(widths[i], len(v))

fmt = "  ".join(f"{{:<{w}}}" for w in widths)
print(fmt.format(*headers))
print(fmt.format(*["-" * w for w in widths]))
for row in str_rows:
    print(fmt.format(*row))

print(f"\n({len(rows)} rows)")
con.close()
