import os
from dotenv import load_dotenv
load_dotenv()

from acquisition.scraper_adapters import BrightDataAPIAdapter, select_scraper_adapter
from acquisition.pagination import fetch_page
from config import RunConfig

# Check if token is set
token = os.getenv('BRIGHTDATA_API_TOKEN')
if token:
    print(f'✅ Found Bright Data API token: {token[:8]}...')
else:
    print('❌ BRIGHTDATA_API_TOKEN not found in .env')
    print('   (This is fine if you are using direct scraping)')

# Test the adapter
print('\n🔍 Testing Bright Data API adapter...')
config = RunConfig(
    query='test',
    target_domain='books.toscrape.com',
    mode='autonomous',
    scraper='brightdata',
    output_dir='results',
    test_injection=False,
    max_retries=3,
    max_pages=50
)

adapter = select_scraper_adapter('books.toscrape.com', config)
print(f'Adapter type: {type(adapter).__name__}')

# Fetch one page
url = 'https://books.toscrape.com'
print(f'Fetching {url}...')
html, status = adapter.fetch(url)
print(f'Status: {status}')
print(f'HTML length: {len(html)} characters')

if len(html) > 0:
    print('✅ Scrape successful!')
else:
    print('⚠️  No HTML returned (likely token missing or API error).')
