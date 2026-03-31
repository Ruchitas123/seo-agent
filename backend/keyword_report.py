"""
SEO Keyword Gap Report — Clear, structured output
Produces:
  1. Your URL rank in SERP
  2. Top 5 SERP URLs with titles
  3. Keywords each top-5 article uses (top 30)
  4. Keyword gaps: present in top-5 but missing from YOUR article
"""

import json
import time
import urllib.parse
import urllib.request
import warnings
warnings.filterwarnings("ignore")

SERPAPI_KEY = "624c346d04c0d680fda0df342fd320657153fa80eb392cf12b1289c3ae57383e"

STOPWORDS = {
    "the","and","for","that","this","with","from","have","are","was","were",
    "has","its","not","but","all","can","will","been","more","also","than",
    "when","into","your","our","their","they","them","there","then","what",
    "which","about","would","could","should","other","these","those","each",
    "some","such","very","just","over","only","both","most","many","much",
    "any","may","did","how","who","one","two","use","get","set","let","put",
    "out","new","see","way","per","via","ago","yet","you","its","—","-","|",
}

def serpapi_search(keyword):
    params = {
        "q": keyword,
        "api_key": SERPAPI_KEY,
        "engine": "google",
        "num": "10",
        "gl": "us",
        "hl": "en",
    }
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def scrape_keywords(url):
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return [], 0, [], []

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        paras = [p.get_text(strip=True) for p in soup.find_all("p")]
        text = " ".join(paras)
        if len(text.split()) < 100:
            text = soup.get_text(separator=" ", strip=True)

        h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]

        words = [w.strip(".,;:!?\"'()[]{}") for w in text.lower().split()]
        words = [w for w in words if w and w not in STOPWORDS and len(w) > 3]

        from collections import Counter
        freq = Counter(words)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        bg_freq = Counter(bigrams)

        # Top unigrams + bigrams by frequency
        top_uni = [w for w, _ in freq.most_common(40)]
        top_bi  = [b for b, c in bg_freq.most_common(20) if c >= 2]

        return top_uni + top_bi, len(text.split()), h1, h2
    except Exception as e:
        return [], 0, [], [str(e)]


def find_your_rank(organic_results, your_url):
    your_domain = urllib.parse.urlparse(your_url).netloc.replace("www.", "")
    for r in organic_results:
        link = r.get("link", "")
        if your_domain in link:
            if your_url.rstrip("/") in link.rstrip("/") or link.rstrip("/") in your_url.rstrip("/"):
                return r.get("position", "?"), link
    # domain match only
    for r in organic_results:
        link = r.get("link", "")
        if your_domain in link:
            return f"{r.get('position', '?')} (different page on same domain)", link
    return "Not in top 10", None


def run_report(keyword, your_url):
    print()
    print("═" * 70)
    print(f"  KEYWORD GAP REPORT")
    print(f"  Keyword : {keyword}")
    print(f"  Your URL: {your_url}")
    print("═" * 70)

    # ── 1. SERP ────────────────────────────────────────────────────────────
    print("\n  [1/4] Fetching real Google SERP via SerpAPI...")
    data = serpapi_search(keyword)
    organic = data.get("organic_results", [])
    paa      = [q.get("question","") for q in data.get("related_questions", [])]
    related  = [r.get("query","") for r in data.get("related_searches", [])]
    print(f"        {len(organic)} organic results returned")

    # ── 2. Your rank ───────────────────────────────────────────────────────
    your_rank, matched_url = find_your_rank(organic, your_url)
    print()
    print("  ┌─ YOUR URL RANKING ─────────────────────────────────────────────")
    print(f"  │  Rank   : #{your_rank}")
    if matched_url:
        print(f"  │  Matched: {matched_url}")
    else:
        print(f"  │  Your URL is NOT ranking in the top 10 for this keyword")
    print("  └────────────────────────────────────────────────────────────────")

    # ── 3. Top 5 SERP ─────────────────────────────────────────────────────
    top5 = organic[:5]
    print()
    print("  ┌─ TOP 5 SERP RESULTS ───────────────────────────────────────────")
    for r in top5:
        print(f"  │  #{r.get('position','?')}  {r.get('title','')[:60]}")
        print(f"  │      {r.get('link','')}")
    print("  └────────────────────────────────────────────────────────────────")

    # ── 4. Scrape your article ────────────────────────────────────────────
    print("\n  [2/4] Scraping YOUR article...")
    your_kws, your_wc, your_h1, your_h2 = scrape_keywords(your_url)
    your_kw_set = set(k.lower() for k in your_kws)
    print(f"        Word count : {your_wc}")
    print(f"        H1         : {your_h1}")
    print(f"        Keywords extracted: {len(your_kws)}")

    # ── 5. Scrape top 5 ──────────────────────────────────────────────────
    print("\n  [3/4] Scraping top 5 competitor articles for keywords...")
    competitor_data = []
    for r in top5:
        url = r.get("link","")
        title = r.get("title","")[:50]
        print(f"        Scraping #{r.get('position')} {title}...")
        kws, wc, h1, h2 = scrape_keywords(url)
        competitor_data.append({
            "rank": r.get("position"),
            "title": r.get("title",""),
            "url": url,
            "word_count": wc,
            "keywords": kws,
            "h1": h1,
            "h2": h2[:6],
        })
        time.sleep(0.5)

    # ── 6. Per-competitor keyword table ──────────────────────────────────
    print()
    print("  ┌─ KEYWORDS USED BY EACH TOP-5 ARTICLE ─────────────────────────")
    for c in competitor_data:
        in_your = sum(1 for k in c["keywords"] if k in your_kw_set)
        missing = [k for k in c["keywords"] if k not in your_kw_set]
        print(f"  │")
        print(f"  │  #{c['rank']}  {c['title'][:60]}")
        print(f"  │      URL       : {c['url']}")
        print(f"  │      Words     : {c['word_count']}")
        print(f"  │      Top keywords (all): {', '.join(c['keywords'][:30])}")
        print(f"  │      In YOUR article  : {in_your}/{len(c['keywords'])} keywords match")
        print(f"  │      Missing from YOU : {', '.join(missing[:20])}")
    print("  └────────────────────────────────────────────────────────────────")

    # ── 7. Gap analysis: terms in ≥2 competitors, absent from your article ─
    print("\n  [4/4] Computing keyword gaps...")
    from collections import Counter
    all_competitor_kws = []
    for c in competitor_data:
        all_competitor_kws.extend(set(c["keywords"]))

    freq = Counter(all_competitor_kws)
    gaps_critical = []  # in 4-5 competitors
    gaps_high     = []  # in 3 competitors
    gaps_medium   = []  # in 2 competitors

    for kw, count in freq.most_common():
        if kw in your_kw_set:
            continue
        if kw in STOPWORDS or len(kw) <= 3:
            continue
        who = [c["title"][:30] for c in competitor_data if kw in c["keywords"]]
        if count >= 4:
            gaps_critical.append((kw, count, who))
        elif count == 3:
            gaps_high.append((kw, count, who))
        elif count == 2:
            gaps_medium.append((kw, count, who))

    print()
    print("  ┌─ KEYWORD GAPS (present in top competitors, MISSING from your article) ─")
    print(f"  │")
    print(f"  │  CRITICAL  — in 4-5/5 competitors: {len(gaps_critical)} gaps")
    for kw, c, who in gaps_critical:
        print(f"  │    [{c}/5] \"{kw}\"")
        print(f"  │          found in: {' | '.join(who)}")

    print(f"  │")
    print(f"  │  HIGH  — in 3/5 competitors: {len(gaps_high)} gaps")
    for kw, c, who in gaps_high[:15]:
        print(f"  │    [{c}/5] \"{kw}\"")

    print(f"  │")
    print(f"  │  MEDIUM  — in 2/5 competitors: {len(gaps_medium)} gaps (top 10 shown)")
    for kw, c, who in gaps_medium[:10]:
        print(f"  │    [{c}/5] \"{kw}\"")
    print("  └────────────────────────────────────────────────────────────────")

    # ── 8. PAA + Related ─────────────────────────────────────────────────
    print()
    print("  ┌─ PEOPLE ALSO ASK (from Google) ───────────────────────────────")
    for q in paa:
        covered = "✓" if any(w in your_kw_set for w in q.lower().split() if len(w)>4) else "✗ GAP"
        print(f"  │  [{covered}] {q}")
    print("  └────────────────────────────────────────────────────────────────")

    print()
    print("  ┌─ RELATED SEARCHES (from Google) ──────────────────────────────")
    for s in related:
        covered = "✓" if any(w in your_kw_set for w in s.lower().split() if len(w)>4) else "✗ GAP"
        print(f"  │  [{covered}] {s}")
    print("  └────────────────────────────────────────────────────────────────")

    # ── 9. Save ───────────────────────────────────────────────────────────
    output = {
        "keyword": keyword,
        "your_url": your_url,
        "your_rank": str(your_rank),
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "top5_serp": [{"rank": c["rank"], "title": c["title"], "url": c["url"], "word_count": c["word_count"], "keywords": c["keywords"]} for c in competitor_data],
        "your_article": {"word_count": your_wc, "h1": your_h1, "h2": your_h2, "keywords": list(your_kw_set)},
        "paa": paa,
        "related_searches": related,
        "gaps": {
            "critical": [{"kw": k, "in_competitors": c, "who": w} for k,c,w in gaps_critical],
            "high":     [{"kw": k, "in_competitors": c, "who": w} for k,c,w in gaps_high],
            "medium":   [{"kw": k, "in_competitors": c, "who": w} for k,c,w in gaps_medium],
        }
    }
    fname = f"report_{keyword.replace(' ','_')}_{int(time.time())}.json"
    with open(fname, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full report saved to: {fname}")
    print()
    print("═" * 70)
    print(f"  SUMMARY: {len(gaps_critical)} critical | {len(gaps_high)} high | {len(gaps_medium)} medium gaps")
    print("═" * 70)


if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║     SEO Keyword Gap Report  v2.0                    ║")
    print("╚══════════════════════════════════════════════════════╝")

    keyword = input("\n  Enter keyword   : ").strip()
    your_url = input("  Enter your URL  : ").strip()

    if not keyword or not your_url:
        print("  ERROR: Both keyword and URL are required.")
    else:
        run_report(keyword, your_url)
