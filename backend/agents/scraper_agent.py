"""
Scraper Agent
-------------
Scrapes competitor pages (top 5 from SERP) and the user's own article.
Raises on network/parse failure — caller decides how to handle.

Returns: (competitor_pages: list[PageData], your_page: PageData)
"""

import re
import time
from collections import Counter

import requests
from bs4 import BeautifulSoup

from config import (
    STOPWORDS, REQUEST_TIMEOUT, SLEEP_BETWEEN_SCRAPES,
    TOP_UNI_LIMIT, TOP_BI_LIMIT, BIGRAM_MIN_COUNT,
    MIN_SCRAPED_WORDS, MAX_HEADING_LENGTH,
)
from models import PageData

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _clean_tokens(text: str, min_len: int = 3) -> list:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if t not in STOPWORDS and len(t) >= min_len and not t.isdigit()]


def _extract_keywords(text: str, h1: list, h2: list, h3: list) -> list:
    all_text = " ".join(h1 + h2 + h3) + " " + text
    tokens   = _clean_tokens(all_text)
    freq     = Counter(tokens)
    bg_freq  = Counter(
        f"{tokens[i]} {tokens[i+1]}"
        for i in range(len(tokens) - 1)
        if tokens[i] not in STOPWORDS and tokens[i+1] not in STOPWORDS
    )
    top_uni = [w for w, _ in freq.most_common(TOP_UNI_LIMIT)]
    top_bi  = [b for b, c in bg_freq.most_common(TOP_BI_LIMIT) if c >= BIGRAM_MIN_COUNT]
    return list(dict.fromkeys(top_uni + top_bi))


def _clean_heading(tag) -> str:
    """Strip anchor/permalink child elements appended to heading text."""
    for child in tag.find_all(["a", "span"], id=True):
        child.decompose()
    for child in tag.find_all(class_=re.compile(r"anchor|permalink|header-link")):
        child.decompose()
    text = tag.get_text(separator=" ", strip=True)
    text = re.sub(r"[a-z0-9]+(?:-[a-z0-9]+){2,}", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _scrape(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))

    h1 = [h for h in (_clean_heading(t) for t in soup.find_all("h1")) if h and len(h) <= MAX_HEADING_LENGTH]
    h2 = [h for h in (_clean_heading(t) for t in soup.find_all("h2")) if h and len(h) <= MAX_HEADING_LENGTH]
    h3 = [h for h in (_clean_heading(t) for t in soup.find_all("h3")) if h and len(h) <= MAX_HEADING_LENGTH]

    return {
        "text": text,
        "h1": h1, "h2": h2, "h3": h3,
        "word_count": len(text.split()),
        "scraped": len(text.split()) >= MIN_SCRAPED_WORDS,
    }


def run(urls_with_meta: list, your_url: str) -> tuple:
    competitor_pages = []

    for item in urls_with_meta:
        try:
            raw = _scrape(item["url"])
            kws = _extract_keywords(raw["text"], raw["h1"], raw["h2"], raw["h3"])
            error = None
        except Exception as e:
            raw   = {"text": "", "h1": [], "h2": [], "h3": [], "word_count": 0, "scraped": False}
            kws   = []
            error = str(e)

        competitor_pages.append(PageData(
            url=item["url"],
            rank=item["rank"],
            title=item["title"],
            word_count=raw["word_count"],
            h1=raw["h1"],
            h2=raw["h2"],
            h3=raw["h3"],
            keywords=kws,
            scraped=raw.get("scraped", False),
            error=error,
        ))
        time.sleep(SLEEP_BETWEEN_SCRAPES)

    raw = _scrape(your_url)
    kws = _extract_keywords(raw["text"], raw["h1"], raw["h2"], raw["h3"])
    your_page = PageData(
        url=your_url,
        rank="yours",
        title="Your Article",
        word_count=raw["word_count"],
        h1=raw["h1"],
        h2=raw["h2"],
        h3=raw["h3"],
        keywords=kws,
        scraped=raw.get("scraped", False),
        error=None,
    )

    return competitor_pages, your_page
