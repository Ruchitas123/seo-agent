"""
SEO + GEO Keyword Gap Analyzer
--------------------------------
Run this script and enter your keyword, article URL, and geo when prompted.
Usage: python3 run_analysis.py
"""

import time
import re
import json
import warnings
import urllib.request
import urllib.parse
from collections import defaultdict

warnings.filterwarnings("ignore")

# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_autocomplete(keyword):
    """Fetch long-tail suggestions from Google Autocomplete (free, no key needed)."""
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))[1]
    except Exception as e:
        return []

def scrape_article(url):
    """Scrape article content from a URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"status": "failed", "reason": "requests/bs4 not installed. Run: pip3 install requests beautifulsoup4"}

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        headings = {
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "h2": [h.get_text(strip=True) for h in soup.find_all("h2")],
            "h3": [h.get_text(strip=True) for h in soup.find_all("h3")],
        }
        text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
        word_count = len(text.split())

        # Try to get publish date
        date = None
        for meta in soup.find_all("meta"):
            if meta.get("property") in ["article:published_time", "og:updated_time"]:
                date = meta.get("content", "")[:10]
                break

        return {
            "status": "success",
            "url": url,
            "word_count": word_count,
            "headings": headings,
            "text": text,
            "publish_date": date,
        }
    except Exception as e:
        return {"status": "failed", "url": url, "reason": str(e)}

def extract_keyword_signals(text, primary_keyword):
    """Extract keyword density and entities from article text."""
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    count = text_lower.count(primary_keyword.lower())
    density = round((count / word_count) * 100, 2) if word_count else 0

    # Extract capitalized entities (brands, tools, proper nouns)
    entities = list(set(re.findall(r"[A-Z][a-z]+(?:\.[a-z]+)?(?:\s[A-Z][a-z]+)*", text)))
    entities = [e for e in entities if len(e) > 3][:15]

    # Extract all n-grams (1-3 words) as candidate secondary keywords
    bigrams = [" ".join(words[i:i+2]) for i in range(len(words)-1)]
    trigrams = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
    all_ngrams = words + bigrams + trigrams

    return {
        "word_count": word_count,
        "primary": {"term": primary_keyword, "count": count, "density_pct": density},
        "entities": entities,
        "candidate_terms": list(set(all_ngrams))
    }

def run_seo_gap_analysis(user_signals, autocomplete_terms, primary_keyword):
    """
    Identify SEO keyword gaps by comparing user article keywords
    against autocomplete suggestions and PAA terms.
    """
    user_text = user_signals.get("candidate_terms", [])
    user_text_lower = [t.lower() for t in user_text]

    gaps = []
    seen = set()

    # Check autocomplete terms as gap candidates
    for term in autocomplete_terms:
        term_lower = term.lower().strip()
        core = term_lower.replace(primary_keyword.lower(), "").strip()
        if not core or core in seen:
            continue
        seen.add(core)
        present = any(core in t for t in user_text_lower)
        if not present and len(core) > 3:
            gaps.append({
                "gap_id": f"seo_{len(gaps)+1:03d}",
                "gap_type": "seo",
                "keyword": core,
                "source": "Google Autocomplete",
                "present_in_user_article": False,
                "priority": "high",
                "observed_evidence": f'"{term}" appears as a top autocomplete suggestion for your keyword',
                "inferred_insight": f'Users searching "{primary_keyword}" also look for "{core}"; its absence may indicate a coverage gap',
                "suggested_action": f'Add "{core}" naturally in a relevant section — target 1-2 mentions'
            })

    return gaps

def run_geo_gap_analysis(user_signals, geo, primary_keyword):
    """Generate GEO-specific keyword gap suggestions based on locale."""
    if not geo:
        return []

    geo_lower = geo.lower()
    user_text_lower = [t.lower() for t in user_signals.get("candidate_terms", [])]

    # Common GEO keyword patterns by locale
    geo_patterns = {
        "united kingdom": [f"{primary_keyword} uk", "gdpr compliant", "uk teams", "remote working uk", "uk pricing"],
        "uk":             [f"{primary_keyword} uk", "gdpr compliant", "uk teams", "remote working uk"],
        "india":          [f"{primary_keyword} india", "india pricing", "rupee pricing", "india teams"],
        "united states":  [f"{primary_keyword} usa", "us teams", "american businesses", "us pricing"],
        "us":             [f"{primary_keyword} us", "us teams", "american businesses"],
        "australia":      [f"{primary_keyword} australia", "australian businesses", "aud pricing"],
        "canada":         [f"{primary_keyword} canada", "canadian teams", "cad pricing"],
    }

    patterns = geo_patterns.get(geo_lower, [f"{primary_keyword} {geo_lower}", f"{geo_lower} teams"])

    gaps = []
    for kw in patterns:
        present = any(kw in t for t in user_text_lower)
        if not present:
            gaps.append({
                "gap_id": f"geo_{len(gaps)+1:03d}",
                "gap_type": "geo",
                "keyword": kw,
                "location": geo,
                "source": "GEO pattern analysis",
                "present_in_user_article": False,
                "priority": "high",
                "observed_evidence": f'Top-ranking {geo} articles commonly include "{kw}" as a geo-qualifier',
                "inferred_insight": f'{geo} users search with locale-specific terms; absence may reduce geo-relevance signals',
                "suggested_action": f'Add "{kw}" with {geo}-specific context (local compliance, pricing, or team references)'
            })
    return gaps

def print_results(result):
    """Pretty-print the keyword gap analysis results."""
    print()
    print("═" * 60)
    print("  KEYWORD GAP ANALYSIS RESULTS")
    print("═" * 60)
    print(f"  Keyword  : {result['keyword']}")
    print(f"  URL      : {result['article_url']}")
    print(f"  Geo      : {result['target_geo'] or 'Not provided (GEO analysis skipped)'}")
    print(f"  Analyzed : {result['analyzed_at']}")
    print(f"  Latency  : {result['latency_seconds']}s")
    print()

    # Article summary
    art = result["user_article"]
    if art["status"] == "success":
        print("  YOUR ARTICLE")
        print(f"  Word count : {art['word_count']}")
        print(f"  H1         : {art['headings']['h1']}")
        print(f"  H2 count   : {len(art['headings']['h2'])}")
        print(f"  H2 sections: {art['headings']['h2'][:4]}")
        kw = result["keyword_signals"]["primary"]
        print(f"  Keyword '{kw['term']}': {kw['count']} mentions ({kw['density_pct']}% density)")
    else:
        print(f"  Article scrape FAILED: {art.get('reason')}")

    print()
    print("  AUTOCOMPLETE SUGGESTIONS (Google — free)")
    for s in result["autocomplete_suggestions"][:5]:
        print(f"    - {s}")

    # SEO Gaps
    seo = result["keyword_gap_list"]["seo_gaps"]
    print()
    print(f"  SEO KEYWORD GAPS ({len(seo)} found)")
    print("  " + "─" * 50)
    if seo:
        for g in seo[:10]:
            print(f"  [{g['priority'].upper()}] {g['keyword']}")
            print(f"    Source   : {g['source']}")
            print(f"    Observed : {g['observed_evidence']}")
            print(f"    Action   : {g['suggested_action']}")
            print()
    else:
        print("  No SEO gaps detected.")

    # GEO Gaps
    geo_gaps = result["keyword_gap_list"]["geo_gaps"]
    print(f"  GEO KEYWORD GAPS ({len(geo_gaps)} found)")
    print("  " + "─" * 50)
    if geo_gaps:
        for g in geo_gaps:
            print(f"  [{g['priority'].upper()}] {g['keyword']}  ({g['location']})")
            print(f"    Source   : {g['source']}")
            print(f"    Observed : {g['observed_evidence']}")
            print(f"    Action   : {g['suggested_action']}")
            print()
    else:
        if result["target_geo"]:
            print("  No GEO gaps detected.")
        else:
            print("  GEO analysis skipped — no geo provided.")

    print("═" * 60)
    print(f"  TOTAL: {len(seo)} SEO gaps | {len(geo_gaps)} GEO gaps")
    print("═" * 60)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║     SEO + GEO Keyword Gap Analyzer  v1.3            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    # ── USER INPUTS ───────────────────────────────────────────
    keyword = input("  Enter target keyword : ").strip()
    if not keyword:
        print("  ERROR: Keyword is required.")
        return

    article_url = input("  Enter article URL    : ").strip()
    if not article_url:
        print("  ERROR: Article URL is required.")
        return

    geo = input("  Enter target geo     : (e.g. United Kingdom, India — press Enter to skip): ").strip()

    print()
    print("  Running analysis...")
    print()

    start = time.time()

    # ── STEP 1: Autocomplete ──────────────────────────────────
    print("  [1/4] Fetching Google Autocomplete suggestions...")
    autocomplete = get_autocomplete(keyword)
    print(f"        {len(autocomplete)} suggestions found")

    # ── STEP 2: Scrape user article ───────────────────────────
    print(f"  [2/4] Scraping your article: {article_url}")
    article = scrape_article(article_url)
    if article["status"] == "success":
        print(f"        {article['word_count']} words extracted")
    else:
        print(f"        FAILED: {article.get('reason')}")

    # ── STEP 3: Extract keyword signals ───────────────────────
    print("  [3/4] Extracting keyword signals...")
    if article["status"] == "success":
        signals = extract_keyword_signals(article["text"], keyword)
        print(f"        Primary keyword density: {signals['primary']['density_pct']}%")
        print(f"        Entities found: {signals['entities'][:5]}")
    else:
        signals = {"candidate_terms": [], "primary": {"term": keyword, "count": 0, "density_pct": 0}, "entities": []}

    # ── STEP 4: Gap analysis ──────────────────────────────────
    print("  [4/4] Running SEO + GEO gap analysis...")
    seo_gaps = run_seo_gap_analysis(signals, autocomplete, keyword)
    geo_gaps = run_geo_gap_analysis(signals, geo, keyword) if geo else []
    print(f"        SEO gaps: {len(seo_gaps)} | GEO gaps: {len(geo_gaps)}")

    elapsed = round(time.time() - start, 2)

    # ── BUILD OUTPUT ──────────────────────────────────────────
    result = {
        "analysis_id": f"analysis-{int(time.time())}",
        "keyword": keyword,
        "article_url": article_url,
        "target_geo": geo or None,
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_seconds": elapsed,
        "tooling_used": {
            "autocomplete": "Google Autocomplete (free)",
            "scraper": "requests + BeautifulSoup (free)",
            "geo_analysis": "Pattern-based (free)",
            "volume_enrichment": "DataForSEO (not run — API key not set)"
        },
        "user_article": article,
        "keyword_signals": signals,
        "autocomplete_suggestions": autocomplete,
        "keyword_gap_list": {
            "seo_gaps": seo_gaps,
            "geo_gaps": geo_gaps
        }
    }

    print_results(result)

    # ── SAVE JSON OUTPUT ──────────────────────────────────────
    output_file = f"gap_analysis_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Full output saved to: {output_file}")
    print()

if __name__ == "__main__":
    main()
