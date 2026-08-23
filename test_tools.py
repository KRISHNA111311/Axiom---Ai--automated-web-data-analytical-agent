import tempfile
import time
from storage.broker import start_broker_process
from agent.tool_functions import (
    get_schema, get_missing_values, get_group_statistics,
    get_binned_statistics, run_profiling_loop
)
from data_contracts import StructuredTask

def test_tools():
    print("🔧 Starting Tool Functions test...")
    db_path = tempfile.mktemp(suffix=".duckdb")
    p, addr = start_broker_process(db_path)
    time.sleep(1)

    # Insert some test data using broker_client_call directly
    from storage.broker import broker_client_call
    records = [
        {"title": "A", "category": "Fiction", "price": 10.0, "currency": "GBP", "rating": 4},
        {"title": "B", "category": "Non-Fiction", "price": 20.0, "currency": "GBP", "rating": 5},
        {"title": "C", "category": "Fiction", "price": 15.0, "currency": "GBP", "rating": 3},
    ]
    broker_client_call("ingest_records", {"records": records}, addr)

    # 1. Test schema
    schema = get_schema()
    print(f"✅ Schema: {schema['row_count']} rows, {len(schema['columns'])} columns")

    # 2. Test missing values
    missing = get_missing_values()
    print(f"✅ Missing values: {missing}")

    # 3. Test group statistics
    stats = get_group_statistics("category", "price")
    print(f"✅ Group stats: {len(stats['groups'])} groups")
    for g in stats['groups']:
        print(f"   {g['group_name']}: n={g['n']}, mean={g['mean']}")

    # 4. Test binned statistics
    binned = get_binned_statistics("price", 5)
    print(f"✅ Binned stats: {len(binned['bin_edges'])} bins")

    # 5. Test full profiling loop
    task = StructuredTask(
        task_type="group_comparison",
        target_domain="test.com",
        group_column="category",
        value_column="price"
    )
    profile = run_profiling_loop(task)
    print(f"✅ Profile bundle:")
    print(f"   Schema rows: {profile.schema_profile.row_count}")
    if profile.group_stats:
        print(f"   Groups: {len(profile.group_stats.groups)}")
    if profile.binned_stats:
        print(f"   Binned stats: {len(profile.binned_stats.bin_edges)} bins")

    # Cleanup
    p.terminate()
    p.join()
    print("✅ Test complete.")

if __name__ == "__main__":
    test_tools()