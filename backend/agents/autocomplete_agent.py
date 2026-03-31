"""
Autocomplete Agent
------------------
Fetches live Google Autocomplete suggestions.
Raises on failure — caller decides how to handle.
"""

import json
import urllib.parse
import urllib.request

from models import AutocompleteResult


def run(keyword: str) -> AutocompleteResult:
    url = (
        "http://suggestqueries.google.com/complete/search"
        f"?client=firefox&q={urllib.parse.quote(keyword)}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        suggestions = json.loads(r.read().decode("utf-8"))[1]
    return AutocompleteResult(suggestions=suggestions)
