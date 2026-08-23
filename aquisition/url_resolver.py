import webbrowser
from typing import Optional
from urllib.parse import urlparse

def validate_and_guide_url(user_input: str) -> Optional[str]:
    """
    Validate user URL.
    - Reject root domains to prevent wasting credits.
    - Guide user to specific pages (page-1.html or product detail).
    """
    if not user_input.startswith(("http://", "https://")):
        print("❌ Invalid URL. Must start with http:// or https://")
        return None

    parsed = urlparse(user_input)

    # --- 1. Root domain (no path or just "/") – REJECT ---
    if parsed.path in ["", "/"]:
        print("\n" + "=" * 60)
        print("🚫 ROOT URL DETECTED – This would waste many credits!")
        print("   Please provide a specific page URL.")
        print("   Examples:")
        print("   - /catalogue/page-1.html  (20 books, 1 credit)")
        print("   - /catalogue/category/books/travel_2/  (1 credit)")
        print("=" * 60)
        webbrowser.open(user_input)
        print("\n✅ Browser opened. Find a specific page and copy its URL.")

        while True:
            new_url = input("\n👉 Paste the specific page URL: ").strip()
            if new_url.startswith(("http://", "https://")):
                return validate_and_guide_url(new_url)
            else:
                print("❌ Invalid format.")

    # --- 2. Category page (ends with / and contains /catalogue/) – Ask for preference ---
    if user_input.endswith("/") and "/catalogue/" in user_input:
        print("\n" + "=" * 60)
        print("📂 CATEGORY PAGE – This will scrape the first page only (20 books, 1 credit).")
        print("   Options:")
        print("     1) Continue (scrape this category page)")
        print("     2) Switch to main catalogue page-1.html (recommended)")
        print("     3) Find a product detail page")
        print("=" * 60)

        choice = input("Enter choice (1/2/3): ").strip()
        if choice == "2":
            base = user_input.split("/catalogue/")[0]
            return f"{base}/catalogue/page-1.html"
        elif choice == "3":
            webbrowser.open(user_input)
            while True:
                new_url = input("Paste product detail URL: ").strip()
                if new_url.startswith(("http://", "https://")):
                    return new_url
        else:
            return user_input

    # --- 3. Specific page (product detail or /page-1.html) – Accept ---
    return user_input