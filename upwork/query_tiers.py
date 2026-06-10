import sqlite3

con = sqlite3.connect("upwork/upwork_parsed.db")
cur = con.execute("""
SELECT
  COALESCE(top_rated_status, 'none')        AS tier,
  COUNT(*)                                  AS n,
  ROUND(AVG(nss_score), 1)                  AS avg_jss,
  MIN(nss_score) || '-' || MAX(nss_score)   AS jss_range,
  SUM(total_earnings IS NOT NULL)           AS earnings_visible,
  ROUND(AVG(total_earnings), 0)             AS avg_earn_visible
FROM profiles
GROUP BY COALESCE(top_rated_status, 'none')
ORDER BY CASE COALESCE(top_rated_status,'none')
           WHEN 'hipo'      THEN 1
           WHEN 'top_rated' THEN 2
           ELSE 3 END
""")

rows = cur.fetchall()
headers = [d[0] for d in cur.description]

# Calculate column widths
widths = [len(h) for h in headers]
str_rows = []
for row in rows:
    str_row = [str(v) if v is not None else "" for v in row]
    str_rows.append(str_row)
    for i, v in enumerate(str_row):
        widths[i] = max(widths[i], len(v))

# Print formatted table
fmt = "  ".join(f"{{:<{w}}}" for w in widths)
print(fmt.format(*headers))
print(fmt.format(*["-" * w for w in widths]))
for row in str_rows:
    print(fmt.format(*row))

con.close()
