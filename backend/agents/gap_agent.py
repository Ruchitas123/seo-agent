"""
Gap Agent — Relevance-first keyword gap extraction
---------------------------------------------------
A keyword gap is only reported if it is RELEVANT to the target keyword.

Relevance rules (at least one must be true):
  1. Came from PAA, Related Searches, or Autocomplete   → always relevant
  2. Is a phrase that shares a token with target keyword → semantically related
  3. Came from a competitor H1/H2/H3 heading            → structural keyword

What is intentionally excluded:
  - Single words tokenized from SERP snippets (sentence words ≠ keywords)
  - Generic body-text words with no connection to the target keyword

Priority:
  CRITICAL = relevant term in (PAA or Related Searches) AND competitor headings
  HIGH     = relevant term in PAA, Related Searches, or Autocomplete
  MEDIUM   = relevant term in competitor H1/H2/H3 headings only
"""

import re
from collections import defaultdict, Counter

from config import STOPWORDS
from models import SerpResult, AutocompleteResult, PageData, GapItem



# ── Helpers ───────────────────────────────────────────────────────────────────

def _tokens(text: str) -> list:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [t for t in text.split() if t not in STOPWORDS and len(t) >= 3 and not t.isdigit()]


def _phrases(text: str) -> list:
    """Extract unigrams + bigrams + trigrams from text."""
    toks = _tokens(text)
    bi = [f"{toks[i]} {toks[i+1]}" for i in range(len(toks) - 1)]
    tri = [f"{toks[i]} {toks[i+1]} {toks[i+2]}" for i in range(len(toks) - 2)]
    return toks + bi + tri


def _kw_tokens(keyword: str) -> set:
    """Non-stopword tokens from the target keyword."""
    return set(_tokens(keyword))


def _is_relevant(term: str, kw_tokens: set) -> bool:
    """
    A term is relevant if it shares enough tokens with the target keyword.

    For single-token keywords: any 1 shared token is enough.
    For multi-token keywords (2+): ALL keyword tokens must appear in the term.
    This prevents "aem forms designer" from matching "forms in sites" just
    because both contain "forms".
    """
    term_tokens = set(_tokens(term))
    overlap = term_tokens & kw_tokens
    required = len(kw_tokens) if len(kw_tokens) >= 2 else 1
    return len(overlap) >= required


def _is_product_specific(term: str, kw_tokens: set) -> bool:
    """A gap term is product-specific if it shares any token with the target keyword."""
    return bool(set(_tokens(term)) & kw_tokens)


# ── Signal extraction ─────────────────────────────────────────────────────────

def _high_quality_serp_signals(serp: SerpResult, autocomplete: AutocompleteResult) -> dict:
    """
    Extract keyword signals ONLY from high-quality SERP sources:
      - PAA questions (full phrase + sub-phrases)
      - Related Searches (full phrase + sub-phrases)
      - Autocomplete suggestions (full phrase)

    SERP snippet sentences are NOT tokenized here — they produce too much noise.
    """
    signals = defaultdict(lambda: {"count": 0, "sources": set()})

    def add(term: str, source: str, weight: int = 1):
        term = re.sub(r"\s+", " ", term.strip().lower().rstrip("?"))
        if term and len(term) >= 3 and not term.isdigit() and term.isascii():
            signals[term]["count"] += weight
            signals[term]["sources"].add(source)

    # PAA — highest quality signal
    for q in serp.paa:
        add(q, "People Also Ask", weight=5)
        for p in _phrases(q):
            add(p, "People Also Ask", weight=3)

    # Related Searches — second highest
    for q in serp.related_searches:
        add(q, "Related Searches", weight=4)
        for p in _phrases(q):
            add(p, "Related Searches", weight=2)

    # Autocomplete — good signal
    for s in autocomplete.suggestions:
        add(s, "Google Autocomplete", weight=3)
        for p in _phrases(s):
            add(p, "Google Autocomplete", weight=1)

    return signals


def _heading_signals(competitor_pages: list) -> dict:
    """
    Extract keyword signals from competitor H1/H2/H3 headings only.
    Each heading is cleaned and processed individually so malformed
    concatenated headings (no whitespace between elements) are skipped.
    """
    signals = defaultdict(lambda: {"count": 0, "sources": set()})

    for page in competitor_pages:
        if not page.scraped:
            continue
        src = f"Competitor H1/H2 #{page.rank}: {page.title[:30]}"

        for heading in (page.h1 + page.h2 + page.h3):
            heading = heading.strip()
            # Skip headings that look like concatenated junk (too long, no spaces, camelCase run-ons)
            if len(heading) > 120:
                continue
            # Skip if heading has suspiciously few spaces relative to length (likely malformed)
            words = heading.split()
            if len(words) == 1 and len(heading) > 25:
                continue
            for p in _phrases(heading):
                # Skip phrases that look like malformed concatenations (no internal spaces in a long token)
                if any(len(tok) > 30 for tok in p.split()):
                    continue
                signals[p]["count"] += 1
                signals[p]["sources"].add(src)

    return signals


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    serp: SerpResult,
    autocomplete: AutocompleteResult,
    competitor_pages: list,
    your_page: PageData,
    keyword: str,
) -> list:
    your_kw_set = set(your_page.keywords)
    kw_toks     = _kw_tokens(keyword)
    kw_lower    = keyword.lower().strip()

    serp_sigs    = _high_quality_serp_signals(serp, autocomplete)
    heading_sigs = _heading_signals(competitor_pages)

    all_terms = set(serp_sigs.keys()) | set(heading_sigs.keys())

    gaps = []

    for term in all_terms:
        # Already in your article — not a gap
        if term in your_kw_set:
            continue
        # Skip the keyword itself
        if term == kw_lower:
            continue
        # Skip very short terms
        if len(term) < 3:
            continue

        in_serp     = term in serp_sigs
        in_headings = term in heading_sigs

        serp_is_paa_or_related = in_serp and any(
            s in ("People Also Ask", "Related Searches", "Google Autocomplete")
            for s in serp_sigs[term]["sources"]
        )

        # ── Relevance gate ────────────────────────────────────────────────
        # Every term must share ALL keyword tokens to be considered relevant.
        # PAA/Related Searches no longer bypass this — Google's related searches
        # can expand into different products (e.g. "aem forms designer" for
        # "forms in sites"), so they must pass the same relevance check.
        if not _is_relevant(term, kw_toks):
            continue

        # ── Priority ──────────────────────────────────────────────────────
        if serp_is_paa_or_related and in_headings:
            priority = "critical"
        elif serp_is_paa_or_related:
            priority = "high"
        elif in_headings:
            priority = "medium"
        else:
            continue

        # Merge sources
        sources = []
        if in_serp:
            sources += sorted(serp_sigs[term]["sources"])
        if in_headings:
            sources += sorted(heading_sigs[term]["sources"])
        sources = list(dict.fromkeys(sources))

        total_count = (
            serp_sigs.get(term, {}).get("count", 0)
            + heading_sigs.get(term, {}).get("count", 0)
        )

        track = "product_specific" if _is_product_specific(term, kw_toks) else "general"

        gaps.append(GapItem(
            keyword=term,
            priority=priority,
            signal_count=total_count,
            sources=sources,
            track=track,
        ))

    # Sort: critical → high → medium, then by signal strength
    order = {"critical": 0, "high": 1, "medium": 2}
    gaps.sort(key=lambda g: (order[g.priority], -g.signal_count))

    # ── Phrase deduplication ──────────────────────────────────────────────
    # If "form version" is a gap, drop standalone "form" and "version"
    phrase_gaps  = [g.keyword for g in gaps if " " in g.keyword]
    phrase_words = {w for phrase in phrase_gaps for w in phrase.split()}

    gaps = [
        g for g in gaps
        if " " in g.keyword               # always keep phrases
        or g.keyword not in phrase_words  # keep single words not covered by a phrase
    ]

    return gaps
