import os
from dotenv import load_dotenv
load_dotenv()

from agent.query_parser import parse_user_query, reparse_with_amendment

def test_parse_query():
    print("🧪 Testing Query Parser (QRY-1)...")
    
    # Test 1: Group comparison with visualizations
    query = "analyze books and tell me the relationship between category and price with visualizations"
    task = parse_user_query(query, "books.toscrape.com")
    print(f"✅ Task: {task}")
    assert task.task_type == "group_comparison"
    assert task.group_column in ["category", "Category"]
    assert task.value_column in ["price", "Price"]
    assert task.visualization_requested == True
    print("Test 1 passed.\n")

    # Test 2: Regression
    query = "predict book price based on rating and availability"
    task = parse_user_query(query, "books.toscrape.com")
    print(f"✅ Task: {task}")
    assert task.task_type == "regression"
    assert task.value_column == "price" or "price" in task.value_column.lower()
    print("Test 2 passed.\n")

    # Test 3: Classification
    query = "classify books by category based on price and rating"
    task = parse_user_query(query, "books.toscrape.com")
    print(f"✅ Task: {task}")
    assert task.task_type == "classification"
    assert task.label_column == "category" or "category" in task.label_column.lower()
    print("Test 3 passed.\n")

    # Test 4: Time-series
    query = "analyze sales trends over time"
    task = parse_user_query(query, "sales.com")
    print(f"✅ Task: {task}")
    assert task.task_type == "timeseries"
    assert task.time_column is not None
    print("Test 4 passed.\n")

    # Test 5: Amendment
    print("🧪 Testing Amendment (QRY-2)...")
    original = parse_user_query("analyze books by category and price", "books.toscrape.com")
    print(f"Original: {original}")
    amended = reparse_with_amendment(original, "also include rating analysis")
    print(f"Amended: {amended}")
    print("Test 5 passed.\n")

    print("🎉 All Phase 11 tests passed!")

if __name__ == "__main__":
    test_parse_query()