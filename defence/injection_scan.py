"""
M2: Injection Defense (SAN-1, SAN-2, SAN-3)
Scans raw HTML for prompt-injection attempts and neutralizes them.
"""

import re
import hashlib
import json
import os
from typing import List, Dict
from datetime import datetime
from bs4 import BeautifulSoup, Comment   # <-- FIX: import Comment

# Pattern lists (detects imperative language, hidden text, directives)
INJECTION_PATTERNS = [
    r"ignore (?:previous|all|prior|above|earlier) (?:instructions|directives|commands)",
    r"system (?:instruction|directive|prompt)",
    r"assistant (?:directive|instruction|override)",
    r"you are (?:now|henceforth|required to)",
    r"do not (?:follow|obey|comply with)",
    r"disregard (?:previous|all|prior|above)",
    r"from now on",
    r"new (?:rule|instruction):",
    r"you will (?:now|always|never)",
]


class InjectionFlag:
    """Data contract for a detected injection."""
    def __init__(self, url: str, location_hint: str, pattern_matched: str, snippet: str):
        self.url = url
        self.location_hint = location_hint
        self.pattern_matched = pattern_matched
        self.snippet = snippet  # <-- FIX: store snippet for neutralization
        # Store only the hash of the snippet, never the raw text (for logging)
        self.snippet_hash = hashlib.sha256(snippet.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "location_hint": self.location_hint,
            "pattern_matched": self.pattern_matched,
            "snippet_hash": self.snippet_hash,
            "timestamp": datetime.now().isoformat()
        }


def scan_for_injection_patterns(raw_html: str) -> List[InjectionFlag]:
    """
    SAN-1: Scan raw HTML for injection patterns.
    """
    flags = []
    soup = BeautifulSoup(raw_html, 'html.parser')

    # 1. Search in visible text
    visible_text = soup.get_text(separator=" ")
    for pattern in INJECTION_PATTERNS:
        matches = re.finditer(pattern, visible_text, re.IGNORECASE)
        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(visible_text), match.end() + 50)
            snippet = visible_text[start:end]
            flags.append(InjectionFlag(
                url="",
                location_hint="visible_text",
                pattern_matched=pattern,
                snippet=snippet
            ))

    # 2. Search in HTML comments – using Comment from bs4
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment_text = str(comment)
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, comment_text, re.IGNORECASE):
                flags.append(InjectionFlag(
                    url="",
                    location_hint="html_comment",
                    pattern_matched=pattern,
                    snippet=comment_text[:200]
                ))

    # 3. Search in hidden elements (display:none or visibility:hidden)
    for element in soup.find_all(style=True):
        style = element.get('style', '')
        if 'display:none' in style.replace(' ', '') or 'visibility:hidden' in style.replace(' ', ''):
            text = element.get_text(strip=True)
            for pattern in INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    flags.append(InjectionFlag(
                        url="",
                        location_hint="hidden_element",
                        pattern_matched=pattern,
                        snippet=text[:200]
                    ))

    return flags


def neutralize_flagged_spans(raw_html: str, flags: List[InjectionFlag]) -> str:
    """
    SAN-2: Neutralize flagged spans by replacing them with a placeholder.
    """
    if not flags:
        return raw_html

    # Replace the exact snippets first
    for flag in flags:
        raw_html = raw_html.replace(flag.snippet, '<!-- INJECTION_NEUTRALIZED -->')
    
    # Also replace the pattern itself as a safety net
    for flag in flags:
        raw_html = re.sub(r'(?i)' + re.escape(flag.pattern_matched), '<!-- INJECTION_NEUTRALIZED -->', raw_html)

    return raw_html


def injection_defense_log(flags: List[InjectionFlag], run_id: str = "default"):
    """
    SAN-3: Log injection flags to logs/injection_flags.jsonl.
    """
    os.makedirs("logs", exist_ok=True)
    log_file = f"logs/injection_flags_{run_id}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        for flag in flags:
            f.write(json.dumps(flag.to_dict()) + "\n")