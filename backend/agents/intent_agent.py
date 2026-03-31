"""
Intent Agent
------------
Detects whether the user's article matches the SERP intent for the keyword.

Logic:
- Parse your article's domain
- Compare against top 3 organic SERP domains
- If 0/3 match AND your domain not present anywhere in top 10 → MISMATCH
- Also detects your exact rank and domain-level rank

Returns: IntentResult
"""

import re
import urllib.parse
from config import STOPWORDS
from models import SerpResult, IntentResult, PageData


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.replace("www.", "").lower()


def run(your_url: str, serp: SerpResult) -> IntentResult:
    your_dom = _domain(your_url)
    organic  = serp.organic

    # Find your rank
    your_rank     = "Not in top 10"
    matched_url   = None

    for r in organic:
        link = r.get("link", "")
        if your_url.rstrip("/") in link.rstrip("/") or link.rstrip("/") in your_url.rstrip("/"):
            your_rank   = f"#{r.get('position', '?')} (exact match)"
            matched_url = link
            break

    if matched_url is None:
        for r in organic:
            link = r.get("link", "")
            if your_dom in _domain(link):
                your_rank   = f"#{r.get('position', '?')} (different page — same domain)"
                matched_url = link
                break

    # Top 3 SERP domains
    top3_domains = [_domain(r.get("link", "")) for r in organic[:3]]

    # Intent match: does your domain appear anywhere in top 10?
    top10_domains = [_domain(r.get("link", "")) for r in organic[:10]]
    domain_in_top10 = any(your_dom in d for d in top10_domains)

    # Detect true intent mismatch: SERP is dominated by a specific type of site
    # (e.g. all results are help/support/docs sites vs your article is a blog)
    # We signal mismatch only when the SERP is clearly a different content type.
    # "Not ranked yet" is NOT a mismatch — it just means the article isn't ranking.
    if domain_in_top10:
        match   = True
        warning = None
    else:
        # Only flag as mismatch if the user's article URL path suggests a different
        # content type from the SERP. If the SERP simply doesn't include the user's
        # domain yet, it is a ranking gap — not an intent mismatch.
        match   = False
        top3_str = ", ".join(d for d in top3_domains[:3] if d)
        warning = (
            f"Your domain ({your_dom}) is not yet ranking in the top 10 for this keyword. "
            f"Top-ranking domains: [{top3_str}]. "
            f"This is a ranking gap, not necessarily an intent mismatch — "
            f"the gap analysis below shows what topics to cover to compete."
        )

    return IntentResult(
        match=match,
        warning=warning,
        your_rank=your_rank,
        matched_url=matched_url,
        serp_domains=top3_domains,
    )


# ── Post-scraping enrichment ───────────────────────────────────────────────────

def _tokens(text: str) -> list:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if t not in STOPWORDS and len(t) >= 3 and not t.isdigit()]


def enrich(intent: IntentResult, your_page: PageData, competitor_pages: list, keyword: str) -> IntentResult:
    """
    Runs after scraping. Enriches IntentResult with:
      - intent_matched_competitor_ranks: competitors whose content overlaps with your page
      - suggested_keywords: refined query variants built from your page's headings

    Intent-matched competitors = scraped pages that share >= 3 keywords with your page.
    These are the only SERP results that are topically relevant to your article.

    Suggested keywords = bigrams/trigrams extracted from your headings that:
      (a) contain at least one token from the original keyword, and
      (b) add specificity beyond the original keyword (at least one new token)
    """
    your_kw_set = set(your_page.keywords)
    kw_toks = set(_tokens(keyword))

    # ── Identify intent-matched competitors ──────────────────────────────────
    matched_ranks = []
    for page in competitor_pages:
        if not page.scraped:
            continue
        overlap = len(set(page.keywords) & your_kw_set)
        if overlap >= 3:
            matched_ranks.append(page.rank)

    # ── Generate suggested keywords from your page's headings ─────────────────
    # Take headings that share a token with the keyword → extract bigrams+trigrams
    # that contain at least one kw token + at least one new token
    suggested = []
    seen = set()
    all_headings = your_page.h1 + your_page.h2 + your_page.h3
    for heading in all_headings:
        htoks = _tokens(heading)
        if not (set(htoks) & kw_toks):
            continue   # heading not related to the keyword
        bigrams  = [f"{htoks[i]} {htoks[i+1]}"            for i in range(len(htoks) - 1)]
        trigrams = [f"{htoks[i]} {htoks[i+1]} {htoks[i+2]}" for i in range(len(htoks) - 2)]
        for phrase in bigrams + trigrams:
            phrase_toks = set(phrase.split())
            has_kw_tok  = bool(phrase_toks & kw_toks)
            is_new      = bool(phrase_toks - kw_toks)   # brings at least one new token
            if has_kw_tok and is_new and phrase not in seen:
                seen.add(phrase)
                suggested.append(phrase)

    intent.intent_matched_competitor_ranks = matched_ranks
    intent.suggested_keywords = suggested[:15]
    return intent
