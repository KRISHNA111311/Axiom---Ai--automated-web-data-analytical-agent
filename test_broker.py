import tempfile
import time
from storage.broker import start_broker_process, broker_client_call

def test_broker():
    print("🔧 Starting broker test...")
    db_path = tempfile.mktemp(suffix=".duckdb")
    p, addr = start_broker_process(db_path)
    print(f"✅ Broker started at {addr}")

    # Ingest some dummy records
    records = [
        {"title": "Book A", "category": "Fiction", "price": 10.0, "currency": "GBP", "rating": 4, "availability": "In stock", "source_url": "http://a.com"},
        {"title": "Book B", "category": "Non-Fiction", "price": 20.0, "currency": "GBP", "rating": 5, "availability": "In stock", "source_url": "http://b.com"},
        {"title": "Book C", "category": "Fiction", "price": 15.0, "currency": "GBP", "rating": 3, "availability": "Out of stock", "source_url": "http://c.com"},
    ]
    result = broker_client_call("ingest_records", {"records": records}, addr)
    print(f"✅ Ingested {result['row_count']} rows")

    # Get schema
    schema = broker_client_call("get_schema", {}, addr)
    print(f"✅ Schema: {schema['row_count']} rows, {len(schema['columns'])} columns")

    # Get group statistics
    stats = broker_client_call("get_group_statistics", {"group_column": "category", "value_column": "price"}, addr)
    print(f"✅ Group stats: {len(stats['groups'])} groups")
    for g in stats['groups']:
        print(f"   {g['group_name']}: n={g['n']}, mean={g['mean']:.2f}")

    # Export snapshot
    snapshot_file = tempfile.mktemp(suffix=".parquet")
    snapshot_result = broker_client_call("export_snapshot", {"file_path": snapshot_file}, addr)
    print(f"✅ Snapshot exported to {snapshot_result['file_path']}")

    # Cleanup
    p.terminate()
    p.join()
    print("✅ Test complete.")

if __name__ == "__main__":
    test_broker()