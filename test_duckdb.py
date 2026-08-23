import duckdb

db_path = 'results/data.duckdb'
conn = duckdb.connect(db_path)

print("=== Table Schema ===")
print(conn.execute("PRAGMA table_info(scraped_records)").fetchall())

print("\n=== Total Rows ===")
print(conn.execute("SELECT COUNT(*) FROM scraped_records").fetchone()[0])

print("\n=== First 5 Rows ===")
print(conn.execute("SELECT * FROM scraped_records LIMIT 5").fetchall())

print("\n=== Distinct Categories (price groups?) ===")
# If 'price' is numeric, show min, max, avg
print(conn.execute("SELECT MIN(price), MAX(price), AVG(price) FROM scraped_records").fetchall())