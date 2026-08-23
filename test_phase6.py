import os
import json
from dotenv import load_dotenv
load_dotenv()

from extraction.extractor import extract_records_from_scraped_data


def main():
    # 1. Check if scraped_data.json exists
    if not os.path.exists("scraped_data.json"):
        print("❌ scraped_data.json not found. Run test_phase5_final.py first.")
        return

    # 2. Load the scraped data
    with open("scraped_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📊 Loaded {len(data)} raw records.")

    # 3. Show available fields in first record (if any)
    if data and len(data) > 0:
        first_record = data[0]
        if isinstance(first_record, dict):
            print("\n📋 Fields in scraped data:")
            for key in first_record.keys():
                print(f"   - {key}: {str(first_record[key])[:50]}...")
            print()

    # 4. Ask user for mapping (optional)
    print("\n📌 You can map scraped fields to target fields (title, category, price, etc.)")
    print("   Format: scraped_field=target_field, scraped_field2=target_field2")
    print("   Example: quote=title, author=category, tags=tags")
    print("   Press Enter to use automatic fuzzy matching.")
    mapping_input = input("\nMapping: ").strip()
    user_mapping = {}
    if mapping_input:
        for pair in mapping_input.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                user_mapping[k.strip()] = v.strip()
        print(f"   Using mapping: {user_mapping}")
    else:
        print("   Using automatic fuzzy matching.")

    # 5. Extract
    records = extract_records_from_scraped_data(data, user_mapping)
    print(f"\n✅ Extracted {len(records)} SanitizedRecords.")

    # 6. Show sample records
    if records:
        print("\n📝 Sample records:")
        for i, rec in enumerate(records[:3]):
            print(f"  {i+1}. Title: {rec.title[:60] if rec.title else '(empty)'}")
            print(f"     Category: {rec.category or '(empty)'}")
            print(f"     Price: {rec.currency} {rec.price}")
            print(f"     Rating: {rec.rating or 'N/A'}")
            print(f"     Source: {rec.source_url[:50]}")
            print()

    # 7. Save to CSV for inspection
    try:
        import pandas as pd
        df = pd.DataFrame([{
            "title": r.title,
            "category": r.category,
            "price": r.price,
            "currency": r.currency,
            "rating": r.rating,
            "availability": r.availability,
            "source_url": r.source_url
        } for r in records])

        df.to_csv("extracted_records.csv", index=False, encoding="utf-8-sig")
        print(f"💾 Saved {len(df)} records to extracted_records.csv")
    except ImportError:
        print("💡 Install pandas to save CSV: pip install pandas")
        # Fallback: save as JSON
        with open("extracted_records.json", "w", encoding="utf-8") as f:
            json.dump([{
                "title": r.title,
                "category": r.category,
                "price": r.price,
                "currency": r.currency,
                "rating": r.rating,
                "availability": r.availability,
                "source_url": r.source_url
            } for r in records], f, indent=2, ensure_ascii=False)
        print("💾 Saved to extracted_records.json")


if __name__ == "__main__":
    main()