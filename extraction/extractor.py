import json
import re
from typing import List, Dict, Any, Optional
from data_contracts import SanitizedRecord

class RecordExtractor:
    def __init__(self, user_mapping: Optional[Dict[str, str]] = None):
        self.user_mapping = user_mapping or {}
        self._build_fallback_mapping()

    def _build_fallback_mapping(self):
        self.fallback_mapping = {
            "title": "title", "name": "title", "headline": "title",
            "quote": "title", "text": "title", "content": "title",
            "product_name": "title", "book_name": "title",
            "category": "category", "type": "category", "section": "category",
            "author": "category", "creator": "category", "genre": "category",
            "price": "price", "cost": "price", "amount": "price", "fee": "price",
            "currency": "currency",
            "rating": "rating", "stars": "rating", "score": "rating",
            "availability": "availability", "stock": "availability", "status": "availability",
            "url": "source_url", "link": "source_url", "source": "source_url", "href": "source_url"
        }

    def _find_field(self, data: Any, target_keys: List[str]) -> Optional[Any]:
        if isinstance(data, dict):
            for key, value in data.items():
                key_lower = key.lower()
                for target in target_keys:
                    if target in key_lower:
                        return value
                result = self._find_field(value, target_keys)
                if result is not None:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_field(item, target_keys)
                if result is not None:
                    return result
        return None

    def _apply_fuzzy_matching(self, scraped_field: str) -> Optional[str]:
        field_lower = scraped_field.lower()
        for pattern, target in self.fallback_mapping.items():
            if pattern in field_lower or field_lower in pattern:
                return target
        return None

    def extract_record(self, raw_data: Dict[str, Any]) -> Optional[SanitizedRecord]:
        record = {}

        for scraped_field, target_field in self.user_mapping.items():
            if scraped_field in raw_data and raw_data[scraped_field] is not None:
                record[target_field] = raw_data[scraped_field]

        if "title" not in record:
            val = self._find_field(raw_data, ["title", "name", "product_name", "book_name"])
            if val is not None:
                record["title"] = str(val)
        if "price" not in record:
            val = self._find_field(raw_data, ["price", "cost", "amount"])
            if val is not None:
                if isinstance(val, dict):
                    for subkey in ["value", "amount", "price"]:
                        if subkey in val:
                            val = val[subkey]
                            break
                record["price"] = self._parse_price(val)
        if "category" not in record:
            val = self._find_field(raw_data, ["category", "type", "section", "author"])
            if val is not None:
                record["category"] = str(val)
        if "rating" not in record:
            val = self._find_field(raw_data, ["rating", "stars", "score"])
            if val is not None:
                record["rating"] = self._parse_rating(val)
        if "currency" not in record:
            val = self._find_field(raw_data, ["currency"])
            if val is not None:
                record["currency"] = str(val)
        if "availability" not in record:
            val = self._find_field(raw_data, ["availability", "stock"])
            if val is not None:
                record["availability"] = str(val)
        if "source_url" not in record:
            val = self._find_field(raw_data, ["url", "link", "href"])
            if val is not None:
                record["source_url"] = str(val)

        for scraped_field, value in raw_data.items():
            if value is None or scraped_field in self.user_mapping:
                continue
            target = self._apply_fuzzy_matching(scraped_field)
            if target and target not in record:
                if target == "price":
                    record[target] = self._parse_price(value)
                elif target == "rating":
                    record[target] = self._parse_rating(value)
                else:
                    record[target] = value

        if "title" not in record:
            record["title"] = ""
        if "price" not in record:
            record["price"] = 0.0
        if "category" not in record:
            record["category"] = ""
        if "currency" not in record:
            record["currency"] = "GBP"

        return SanitizedRecord(
            title=str(record.get("title", "")),
            category=str(record.get("category", "")),
            price=self._parse_price(record.get("price", 0.0)),
            currency=str(record.get("currency", "GBP")),
            rating=self._parse_rating(record.get("rating")),
            availability=str(record.get("availability", "")) if record.get("availability") else None,
            source_url=str(record.get("source_url", ""))
        )

    def _parse_price(self, value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^0-9.]', '', value)
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0

    def _parse_rating(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            rating_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
            try:
                if value.lower() in rating_map:
                    return rating_map[value.lower()]
                return int(value)
            except ValueError:
                return None
        return None

    def extract_batch(self, raw_data: List[Dict[str, Any]]) -> List[SanitizedRecord]:
        records = []
        for item in raw_data:
            rec = self.extract_record(item)
            if rec:
                records.append(rec)
        return records

    def extract_from_json_file(self, file_path: str) -> List[SanitizedRecord]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key in ["data", "items", "records", "results", "hits", "quotes", "products"]:
                if key in data and isinstance(data[key], list):
                    return self.extract_batch(data[key])
            return self.extract_batch([data])
        elif isinstance(data, list):
            return self.extract_batch(data)
        else:
            return []

def extract_records_from_scraped_data(
    json_data: Any,
    user_mapping: Optional[Dict[str, str]] = None
) -> List[SanitizedRecord]:
    extractor = RecordExtractor(user_mapping)
    if isinstance(json_data, str):
        if json_data.strip().endswith(('.json', '.txt')):
            return extractor.extract_from_json_file(json_data)
        try:
            parsed = json.loads(json_data)
            if isinstance(parsed, list):
                return extractor.extract_batch(parsed)
            elif isinstance(parsed, dict):
                return extractor.extract_batch([parsed])
        except json.JSONDecodeError:
            return []
    elif isinstance(json_data, list):
        return extractor.extract_batch(json_data)
    elif isinstance(json_data, dict):
        return extractor.extract_batch([json_data])
    return []

# ============================================================
# HTML Parser for books.toscrape.com (for Direct HTTP)
# ============================================================

def parse_books_toscrape_html(html: str, url: str = "") -> List[Dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    books = []
    category = "Unknown"
    breadcrumb = soup.find('ul', class_='breadcrumb')
    if breadcrumb:
        items = breadcrumb.find_all('li')
        if len(items) >= 3:
            category = items[-1].get_text(strip=True)
    elif "category/books/" in url:
        match = re.search(r'/category/books/([^/]+)/', url)
        if match:
            category = match.group(1).replace('_', ' ').title()

    for article in soup.find_all('article', class_='product_pod'):
        h3 = article.find('h3')
        title = h3.find('a').get('title', '') if h3 and h3.find('a') else ''
        price_tag = article.find('p', class_='price_color')
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            cleaned = re.sub(r'[^\d.]', '', price_text)
            price = float(cleaned) if cleaned else 0.0
        else:
            price = 0.0
        books.append({
            "book_name": title,
            "price": price,
            "category": category,
            "source_url": url
        })
    return books