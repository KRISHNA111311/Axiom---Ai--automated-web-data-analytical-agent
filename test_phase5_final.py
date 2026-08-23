import os
import json
from dotenv import load_dotenv
load_dotenv()

from acquisition.url_resolver import validate_and_guide_url
from acquisition.scraper_adapters import select_scraper_adapter, BrightDataCLIAdapter
from config import RunConfig

def main():
    # 1. User input URL
    user_url = input("Enter the target URL (e.g., https://books.toscrape.com/): ").strip()
    target_url = validate_and_guide_url(user_url)
    if not target_url:
        return

    print(f"\n✅ Final URL to scrape: {target_url}")

    # 2. Choose mode: target records or max pages
    mode = input("\nUse (1) target_records or (2) max_pages? (1/2): ").strip()
    if mode == "1":
        target_records = int(input("Number of records needed: ").strip() or 20)
        max_pages = None
    else:
        max_pages = int(input("Number of pages to scrape: ").strip() or 1)
        target_records = None

    # 3. Fields
    fields_input = input(
        "\nEnter fields to extract (comma-separated, or press Enter for defaults): "
    ).strip()
    fields = [f.strip() for f in fields_input.split(",")] if fields_input else None

    # 4. Build config
    config = RunConfig(
        query="test",
        target_domain="books.toscrape.com",
        mode="autonomous",
        scraper="brightdata",
        output_dir="results",
        test_injection=False,
        max_retries=3,
        max_pages=max_pages,
        target_records=target_records,
        fields=fields,
        sample_durations=[40, 70, 100],
        safety_factor=1.2
    )

    # 5. Select adapter
    adapter = select_scraper_adapter("books.toscrape.com", config)
    print(f"\nUsing adapter: {type(adapter).__name__}")

    # 6. Fetch
    try:
        json_str, status = adapter.fetch(target_url)
    except Exception as e:
        print(f"❌ Adapter error: {e}")
        return

    if status == 200:
        data = json.loads(json_str)
        print(f"\n✅ Scraped {len(data)} records.")
        if data:
            print("First record:", json.dumps(data[0], indent=2)[:500])
        # Save output
        with open("scraped_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Saved to scraped_data.json")
    else:
        print(f"❌ Scrape failed with status {status}")

if __name__ == "__main__":
    main()