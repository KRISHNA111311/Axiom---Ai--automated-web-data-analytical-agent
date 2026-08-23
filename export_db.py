import duckdb

db_path = "results/data.duckdb"
conn = duckdb.connect(db_path)

# 1. Show schema
print("=== Schema ===")
print(conn.execute("PRAGMA table_info(scraped_records)").fetchall())

# 2. Count rows
count = conn.execute("SELECT COUNT(*) FROM scraped_records").fetchone()[0]
print(f"\nTotal rows: {count}")

# 3. Export to CSV (full)
conn.execute("COPY scraped_records TO 'results/exported_data.csv' (HEADER, DELIMITER ',')")
print("\n✅ Full data exported to results/exported_data.csv")

# 4. Also print a sample as CSV to console
if count > 0:
    print("\n=== First 5 rows (CSV format) ===")
    df = conn.execute("SELECT * FROM scraped_records LIMIT 5").df()
    print(df.to_csv(index=False))