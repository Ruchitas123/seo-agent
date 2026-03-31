"""
SERP Agent
----------
Fetches real Google SERP data via SerpAPI.
Returns: SerpResult (organic results, PAA, related searches, raw response)
"""

import json
import urllib.parse
import urllib.request

from config import SERPAPI_KEY, SERP_NUM
from models import SerpResult


def run(keyword: str, geo: str = "us") -> SerpResult:
    params = {
        "q":       keyword,
        "api_key": SERPAPI_KEY,
        "engine":  "google",
        "num":     SERP_NUM,
        "gl":      geo,
        "hl":      "en",
    }
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))

    organic = data.get("organic_results", [])
    paa = [q.get("question", "") for q in data.get("related_questions", []) if q.get("question")]
    related = [r.get("query", "") for r in data.get("related_searches", []) if r.get("query")]

    return SerpResult(organic=organic, paa=paa, related_searches=related, raw=data)
