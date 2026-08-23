"""
ACQ‑2, ACQ‑3, ACQ‑4: Pagination discovery, page fetching, and full acquisition.
"""

import time
from typing import List
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from data_contracts import RawPageBundle
from acquisition.scraper_adapters import ScraperAdapter, DirectHTTPAdapter


def discover_pagination(
    seed_url: str,
    adapter: ScraperAdapter,
    next_link_selector: str = "a[rel='next']",
    max_pages: int = 50
) -> List[str]:
    urls = []
    current_url = seed_url
    for _ in range(max_pages):
        urls.append(current_url)
        html, status = adapter.fetch(current_url)
        if status != 200 or not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        next_tag = soup.select_one(next_link_selector)
        if not next_tag:
            break
        next_href = next_tag.get("href")
        if not next_href:
            break
        next_url = urljoin(current_url, next_href)
        if next_url == current_url or next_url in urls:
            break
        current_url = next_url
        time.sleep(0.5)
    return urls


def fetch_page(url: str, adapter: ScraperAdapter) -> RawPageBundle:
    html, status = adapter.fetch(url)
    return RawPageBundle(
        url=url,
        html=html,
        fetched_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        source="direct" if isinstance(adapter, DirectHTTPAdapter) else "brightdata",
        status_code=status
    )


def acquire_raw_target(
    structured_task,
    adapter: ScraperAdapter,
    max_pages_global: int = 50
) -> List[RawPageBundle]:
    """
    ACQ-4: Acquire the full target.

    If the user provides a full URL (e.g., Amazon search with query parameters),
    it uses that URL directly and discovers pagination from it.
    Otherwise, it treats the input as a domain, discovers categories from the homepage,
    and fetches all pages within each category.

    :param structured_task: The analysis task (contains target_domain, etc.)
    :param adapter: The scraper adapter (Direct or Bright Data)
    :param max_pages_global: Maximum number of pages to fetch (default 50)
    """
    raw_input = structured_task.target_domain

    if "?" in raw_input and "=" in raw_input:
        homepage_url = raw_input
        print(f"🔍 Using provided full URL directly: {homepage_url}")
        use_full_url = True
    else:
        if not raw_input.startswith("http"):
            raw_input = f"https://{raw_input}"
        homepage_url = raw_input
        print(f"🔍 Discovering categories from: {homepage_url}")
        use_full_url = False

    print(f"📡 Fetching: {homepage_url}")
    html, status = adapter.fetch(homepage_url)
    if status != 200 or not html:
        print("❌ Failed to fetch the starting page. Aborting acquisition.")
        return []

    all_page_urls = []

    if use_full_url:
        print("📄 Discovering pagination from the provided URL...")
        page_urls = discover_pagination(
            seed_url=homepage_url,
            adapter=adapter,
            next_link_selector="a[rel='next']",
            max_pages=max_pages_global
        )
        all_page_urls.extend(page_urls)
    else:
        soup = BeautifulSoup(html, "html.parser")
        category_links = []

        side_nav = soup.select_one("ul.nav.nav-list")
        if side_nav:
            for a_tag in side_nav.find_all("a"):
                href = a_tag.get("href")
                if href and "catalogue" in href and "category" in href:
                    full_url = urljoin(homepage_url, href)
                    category_links.append(full_url)
        else:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "category" in href and "catalogue" in href:
                    full_url = urljoin(homepage_url, href)
                    if full_url not in category_links:
                        category_links.append(full_url)

        print(f"📂 Found {len(category_links)} categories.")

        for cat_url in category_links:
            page_urls = discover_pagination(
                seed_url=cat_url,
                adapter=adapter,
                next_link_selector="a[rel='next']",
                max_pages=max_pages_global
            )
            all_page_urls.extend(page_urls)

    print(f"📄 Total pages to fetch: {len(all_page_urls)}")

    all_page_bundles = []
    for idx, url in enumerate(all_page_urls, 1):
        print(f"  Fetching page {idx}/{len(all_page_urls)}: {url}")
        bundle = fetch_page(url, adapter)
        all_page_bundles.append(bundle)
        time.sleep(0.3)

    print(f"✅ Acquired {len(all_page_bundles)} page bundles.")
    return all_page_bundles


def check_scraper_dependency(flags) -> bool:
    return flags.scraper_enabled