"""
SERP-Driven Keyword Gap Analyzer
---------------------------------
Keywords are extracted from REAL-TIME Google SERP signals:
  1. Organic result titles + snippets   (what Google deems relevant)
  2. People Also Ask questions          (real user intent)
  3. Related Searches                   (Google's own keyword clusters)
  4. Google Autocomplete                (live search suggestions)
  5. Competitor page content (top 5)    (supplemental depth)

All data via SerpAPI (real Google) + Google Autocomplete API.
"""

import json
import time
import re
import urllib.parse
import urllib.request
import warnings
from collections import Counter, defaultdict

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
    "here","a","an","in","of","to","is","it","be","at","by","or","on","do",
    "as","we","he","she","so","if","up","no","me","my","us","am","go","re",
    "i","s","t","d","ll","ve","m","https","http","www","com","org","html",
    "like","feel","make","give","work","time","since","part","allow","used",
    "different","where","through","it's","i'm","you're","we're","don't",
    "isn't","aren't","wasn't","weren't","hasn't","haven't","hadn't","won't",
}

# ── API calls ──────────────────────────────────────────────────────────────────

def serpapi_call(params):
    params["api_key"] = SERPAPI_KEY
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def google_autocomplete(keyword):
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))[1]
    except:
        return []

def scrape_page(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        paras = [p.get_text(strip=True) for p in soup.find_all("p")]
        text = " ".join(paras)
        if len(text.split()) < 100:
            text = soup.get_text(separator=" ", strip=True)
        h1 = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2 = [h.get_text(strip=True) for h in soup.find_all("h2")]
        h3 = [h.get_text(strip=True) for h in soup.find_all("h3")]
        return {"text": text, "h1": h1, "h2": h2, "h3": h3, "word_count": len(text.split())}
    except Exception as e:
        return {"text": "", "h1": [], "h2": [], "h3": [], "word_count": 0, "error": str(e)}

# ── Keyword extraction ─────────────────────────────────────────────────────────

def clean_tokens(text, min_len=3):
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) >= min_len and not t.isdigit()]

def extract_phrases(text, min_len=3):
    """Extract meaningful unigrams and bigrams from text."""
    tokens = clean_tokens(text, min_len)
    unigrams = tokens
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)
               if tokens[i] not in STOPWORDS and tokens[i+1] not in STOPWORDS]
    return unigrams + bigrams

def extract_from_serp(data, keyword):
    """Extract all keyword signals directly from the SERP response."""
    signals = defaultdict(lambda: {"count": 0, "sources": []})

    kw_lower = keyword.lower()

    def add(term, source):
        term = term.strip().lower()
        term = re.sub(r'\s+', ' ', term)
        if term and len(term) >= 3 and term not in STOPWORDS and not term.isdigit():
            signals[term]["count"] += 1
            if source not in signals[term]["sources"]:
                signals[term]["sources"].append(source)

    # 1. Organic titles + snippets
    for r in data.get("organic_results", []):
        rank = r.get("position", "?")
        src = f"SERP snippet #{rank}"
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        for phrase in extract_phrases(title + " " + snippet):
            # strip the exact keyword from phrase to find additive terms
            core = phrase.replace(kw_lower, "").strip()
            add(phrase, src)
            if core and core != phrase:
                add(core, src)

    # 2. People Also Ask
    for q in data.get("related_questions", []):
        question = q.get("question", "")
        answer = q.get("snippet", "")
        for phrase in extract_phrases(question + " " + answer):
            add(phrase, "People Also Ask")
        # also add the full question as a keyword phrase
        q_clean = re.sub(r'[^\w\s]', ' ', question.lower()).strip()
        if q_clean:
            add(q_clean, "People Also Ask (question)")

    # 3. Related Searches
    for r in data.get("related_searches", []):
        query = r.get("query", "")
        for phrase in extract_phrases(query):
            add(phrase, "Related Searches")
        # add the full related search as a phrase
        q_clean = re.sub(r'[^\w\s]', ' ', query.lower()).strip()
        if q_clean:
            add(q_clean, "Related Searches (phrase)")

    # 4. Knowledge graph / answer box
    for field in ["answer_box", "knowledge_graph"]:
        box = data.get(field, {})
        if isinstance(box, dict):
            text = " ".join(str(v) for v in box.values() if isinstance(v, str))
            for phrase in extract_phrases(text):
                add(phrase, f"Google {field}")

    return signals

def extract_from_page(page_data, rank):
    """Extract keywords from scraped page content."""
    signals = defaultdict(lambda: {"count": 0, "sources": []})
    src = f"Competitor page #{rank}"

    all_text = (
        " ".join(page_data.get("h1", [])) + " " +
        " ".join(page_data.get("h2", [])) + " " +
        " ".join(page_data.get("h3", [])) + " " +
        page_data.get("text", "")
    )

    tokens = clean_tokens(all_text)
    freq = Counter(tokens)
    # bigrams
    bigram_freq = Counter(
        f"{tokens[i]} {tokens[i+1]}"
        for i in range(len(tokens)-1)
        if tokens[i] not in STOPWORDS and tokens[i+1] not in STOPWORDS
    )

    for term, count in freq.most_common(50):
        signals[term]["count"] += count
        if src not in signals[term]["sources"]:
            signals[term]["sources"].append(src)

    for term, count in bigram_freq.most_common(30):
        if count >= 2:
            signals[term]["count"] += count
            if src not in signals[term]["sources"]:
                signals[term]["sources"].append(src)

    return signals

def merge_signals(*signal_dicts):
    merged = defaultdict(lambda: {"count": 0, "sources": []})
    for sd in signal_dicts:
        for term, data in sd.items():
            merged[term]["count"] += data["count"]
            for s in data["sources"]:
                if s not in merged[term]["sources"]:
                    merged[term]["sources"].append(s)
    return merged

# ── Your article keywords ──────────────────────────────────────────────────────

def get_your_keywords(url):
    print(f"  Scraping your article...")
    page = scrape_page(url)
    if page["word_count"] == 0:
        return set(), page
    all_text = (
        " ".join(page.get("h1", [])) + " " +
        " ".join(page.get("h2", [])) + " " +
        " ".join(page.get("h3", [])) + " " +
        page.get("text", "")
    )
    tokens = clean_tokens(all_text)
    bigrams = [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens)-1)
               if tokens[i] not in STOPWORDS and tokens[i+1] not in STOPWORDS]
    kw_set = set(tokens + bigrams)
    print(f"  Your article: {page['word_count']} words, {len(kw_set)} unique terms")
    return kw_set, page

# ── Main report ────────────────────────────────────────────────────────────────

def run_report(keyword, your_url):
    print()
    print("═" * 72)
    print(f"  SERP-DRIVEN KEYWORD GAP REPORT")
    print(f"  Keyword  : {keyword}")
    print(f"  Your URL : {your_url[:70]}")
    print("═" * 72)

    # ── Step 1: Live Google SERP via SerpAPI ──────────────────────────────
    print(f"\n  [1/5] Fetching live Google SERP for \"{keyword}\"...")
    serp_data = serpapi_call({"q": keyword, "engine": "google", "num": "10", "gl": "us", "hl": "en"})
    organic = serp_data.get("organic_results", [])
    paa     = serp_data.get("related_questions", [])
    related = serp_data.get("related_searches", [])
    print(f"        {len(organic)} organic results | {len(paa)} PAA | {len(related)} related searches")

    # ── Step 2: Google Autocomplete ───────────────────────────────────────
    print(f"  [2/5] Fetching Google Autocomplete suggestions...")
    autocomplete = google_autocomplete(keyword)
    print(f"        {len(autocomplete)} suggestions: {autocomplete[:5]}")

    # ── Step 3: Extract keywords from SERP data ───────────────────────────
    print(f"  [3/5] Extracting keywords from SERP titles, snippets, PAA, related searches...")
    serp_signals = extract_from_serp(serp_data, keyword)
    print(f"        {len(serp_signals)} unique keyword signals from SERP")

    # ── Step 4: Scrape top 5 competitor pages ─────────────────────────────
    print(f"  [4/5] Scraping top 5 competitor pages...")
    top5 = organic[:5]
    page_signals_list = []
    competitor_pages = []
    for r in top5:
        url = r.get("link","")
        title = r.get("title","")
        rank = r.get("position","?")
        print(f"        #{rank} {title[:55]}...")
        page = scrape_page(url)
        page["rank"] = rank
        page["title"] = title
        page["url"] = url
        competitor_pages.append(page)
        if page["word_count"] > 50:
            page_signals_list.append(extract_from_page(page, rank))
            print(f"             → {page['word_count']} words scraped ✓")
        else:
            print(f"             → JS-rendered / blocked ✗")
        time.sleep(0.5)

    # ── Step 5: Your article ──────────────────────────────────────────────
    print(f"  [5/5] Analyzing your article...")
    your_kws, your_page = get_your_keywords(your_url)

    # ── Merge all competitor signals ──────────────────────────────────────
    all_signals = merge_signals(serp_signals, *page_signals_list)

    # Also add autocomplete phrases
    for suggestion in autocomplete:
        for phrase in extract_phrases(suggestion):
            all_signals[phrase]["count"] += 1
            if "Google Autocomplete" not in all_signals[phrase]["sources"]:
                all_signals[phrase]["sources"].append("Google Autocomplete")
        s_clean = re.sub(r'[^\w\s]', ' ', suggestion.lower()).strip()
        if s_clean:
            all_signals[s_clean]["count"] += 1
            if "Google Autocomplete (phrase)" not in all_signals[s_clean]["sources"]:
                all_signals[s_clean]["sources"].append("Google Autocomplete (phrase)")

    # ── Identify gaps ─────────────────────────────────────────────────────
    kw_lower = keyword.lower()
    gaps = []
    for term, data in all_signals.items():
        if term in your_kws:
            continue
        if term == kw_lower or kw_lower in term:
            continue  # skip the keyword itself
        if len(term) < 3:
            continue
        sources = data["sources"]
        count = data["count"]

        # Priority based on source quality
        serp_source = any("SERP snippet" in s or "People Also Ask" in s or
                          "Related Searches" in s or "Google" in s for s in sources)
        page_source = any("Competitor page" in s for s in sources)

        if serp_source and page_source:
            priority = "critical"
        elif serp_source:
            priority = "high"
        elif page_source and count >= 3:
            priority = "high"
        elif page_source and count >= 2:
            priority = "medium"
        else:
            continue  # skip low-signal terms

        gaps.append({
            "keyword": term,
            "priority": priority,
            "signal_count": count,
            "sources": sources,
        })

    # Sort: critical > high > medium, then by signal count
    order = {"critical": 0, "high": 1, "medium": 2}
    gaps.sort(key=lambda x: (order[x["priority"]], -x["signal_count"]))

    # ── Print report ──────────────────────────────────────────────────────
    your_rank_label, matched = find_rank(organic, your_url)

    print()
    print("┌─ YOUR RANKING ─────────────────────────────────────────────────────")
    print(f"│  Rank : {your_rank_label}")
    if matched:
        print(f"│  Url  : {matched}")
    print("└────────────────────────────────────────────────────────────────────")

    print()
    print("┌─ TOP 5 SERP RESULTS ───────────────────────────────────────────────")
    for r in top5:
        print(f"│  #{r.get('position')}  {r.get('title','')[:60]}")
        print(f"│       {r.get('link','')}")
        snip = r.get("snippet","")
        if snip:
            print(f"│       Snippet: {snip[:100]}...")
    print("└────────────────────────────────────────────────────────────────────")

    print()
    print("┌─ GOOGLE AUTOCOMPLETE SUGGESTIONS ─────────────────────────────────")
    for s in autocomplete:
        covered = "✓" if s.lower() in your_kws else "✗ GAP"
        print(f"│  [{covered}]  {s}")
    print("└────────────────────────────────────────────────────────────────────")

    print()
    print("┌─ PEOPLE ALSO ASK ──────────────────────────────────────────────────")
    for q in paa:
        question = q.get("question","")
        covered = "✓" if any(w in your_kws for w in clean_tokens(question) if len(w)>4) else "✗ GAP"
        print(f"│  [{covered}]  {question}")
    print("└────────────────────────────────────────────────────────────────────")

    print()
    print("┌─ RELATED SEARCHES ─────────────────────────────────────────────────")
    for r in related:
        query = r.get("query","")
        covered = "✓" if any(w in your_kws for w in clean_tokens(query) if len(w)>4) else "✗ GAP"
        print(f"│  [{covered}]  {query}")
    print("└────────────────────────────────────────────────────────────────────")

    # ── Keyword gaps table ────────────────────────────────────────────────
    critical = [g for g in gaps if g["priority"] == "critical"]
    high     = [g for g in gaps if g["priority"] == "high"]
    medium   = [g for g in gaps if g["priority"] == "medium"]

    LABELS = {"critical": "🔴 CRITICAL", "high": "🟠 HIGH", "medium": "🟡 MEDIUM"}

    print()
    print("┌─ KEYWORD GAP LIST — ADD THESE TO YOUR ARTICLE ────────────────────")
    print(f"│")
    print(f"│  HOW TO READ: Priority is based on WHERE Google signals the keyword")
    print(f"│  CRITICAL = in SERP snippets/PAA/Related AND competitor pages")
    print(f"│  HIGH     = in SERP signals (snippets, PAA, related searches)")
    print(f"│  MEDIUM   = in competitor page content only (3+ mentions)")
    print(f"│")

    for label, group in [("CRITICAL", critical), ("HIGH", high[:20]), ("MEDIUM", medium[:15])]:
        print(f"│  ── {label} ({len(group)} keywords) {'──' if label=='MEDIUM' else ''}")
        if not group:
            print(f"│     (none)")
        for g in group:
            src_short = " | ".join(set(
                s.split(" #")[0].replace("(phrase)","").replace("(question)","").strip()
                for s in g["sources"]
            ))
            print(f"│     \"{g['keyword']}\"")
            print(f"│          Sources: {src_short}")
        print(f"│")
    print("└────────────────────────────────────────────────────────────────────")

    print()
    print("═" * 72)
    print(f"  TOTAL GAPS: {len(critical)} critical | {len(high)} high | {len(medium)} medium")
    print(f"  All sourced from live Google SERP + Autocomplete + page scraping")
    print("═" * 72)

    # ── Save ──────────────────────────────────────────────────────────────
    output = {
        "keyword": keyword,
        "your_url": your_url,
        "your_rank": your_rank_label,
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_sources": [
            "Google SERP organic titles + snippets (via SerpAPI)",
            "People Also Ask (via SerpAPI)",
            "Related Searches (via SerpAPI)",
            "Google Autocomplete (live)",
            "Competitor page scraping (top 5)",
        ],
        "top5_serp": [{"rank": c["rank"], "title": c["title"], "url": c["url"], "word_count": c["word_count"]} for c in competitor_pages],
        "autocomplete": autocomplete,
        "paa": [q.get("question","") for q in paa],
        "related_searches": [r.get("query","") for r in related],
        "your_article": {
            "word_count": your_page.get("word_count", 0),
            "h1": your_page.get("h1", []),
            "h2": your_page.get("h2", []),
        },
        "keyword_gaps": {
            "critical": critical,
            "high": high,
            "medium": medium,
        }
    }
    fname = f"serp_report_{keyword.replace(' ','_')}_{int(time.time())}.json"
    with open(fname, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Report saved to: {fname}")
    return output

def find_rank(organic, your_url):
    your_domain = urllib.parse.urlparse(your_url).netloc.replace("www.", "")
    for r in organic:
        link = r.get("link","")
        if your_url.rstrip("/") in link.rstrip("/") or link.rstrip("/") in your_url.rstrip("/"):
            return f"#{r.get('position')} (exact match)", link
    for r in organic:
        link = r.get("link","")
        if your_domain in link:
            return f"#{r.get('position')} (different page on same domain)", link
    return "Not in top 10", None

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   SERP-Driven Keyword Gap Analyzer  v3.0                       ║")
    print("║   Sources: Google SERP + PAA + Related + Autocomplete + Pages  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    keyword  = input("\n  Enter keyword   : ").strip()
    your_url = input("  Enter your URL  : ").strip()

    if not keyword or not your_url:
        print("  ERROR: Both keyword and URL are required.")
    else:
        run_report(keyword, your_url)
