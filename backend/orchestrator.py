"""
Orchestrator
------------
Coordinates all 5 agents sequentially and returns a single AnalysisResult.

  Step 1 — serp_agent      : fetch Google SERP (organic, PAA, related searches)
  Step 2 — autocomplete_agent : fetch Google Autocomplete suggestions
  Step 3 — intent_agent    : detect intent mismatch, find your rank
  Step 4 — scraper_agent   : scrape top 5 competitor pages + your article
  Step 5 — gap_agent       : compute keyword gaps (critical / high / medium)

Usage as a library:
    from orchestrator import run_analysis
    result = run_analysis("interactive communications AEM", "https://...")

Usage as CLI:
    python3 orchestrator.py "interactive communications AEM" "https://..."
"""

import sys
import time
import json
from datetime import datetime, timezone
from typing import Callable, Optional

from models import AnalysisResult
from agents import serp_agent, autocomplete_agent, intent_agent, scraper_agent, gap_agent


def run_analysis(
    keyword: str,
    your_url: str,
    geo: str,
    on_step: Optional[Callable[[int, str], None]] = None,
) -> AnalysisResult:
    """
    Run the full pipeline.

    Args:
        keyword   : target keyword to analyze
        your_url  : URL of your article
        geo       : 2-letter country code for Google SERP locale (default: "us")
        on_step   : optional callback(step_num, description) for progress reporting
                    e.g. used by the Streamlit dashboard to update UI
    """

    def step(n, desc):
        if on_step:
            on_step(n, desc)

    t0 = time.time()

    # ── Step 1: SERP ──────────────────────────────────────────────────────────
    step(1, f"Fetching live Google SERP for \"{keyword}\"...")
    serp = serp_agent.run(keyword, geo)

    # ── Step 2: Autocomplete ──────────────────────────────────────────────────
    step(2, "Fetching Google Autocomplete suggestions...")
    autocomplete = autocomplete_agent.run(keyword)

    # ── Step 3: Intent detection ──────────────────────────────────────────────
    step(3, "Detecting search intent and your article rank...")
    intent = intent_agent.run(your_url, serp)

    # ── Step 4: Scrape competitor pages + your article ────────────────────────
    step(4, f"Scraping top {min(5, len(serp.organic))} competitor pages...")
    urls_with_meta = [
        {"url": r.get("link", ""), "rank": r.get("position", "?"), "title": r.get("title", "")}
        for r in serp.organic[:5]
        if r.get("link")
    ]
    competitor_pages, your_page = scraper_agent.run(urls_with_meta, your_url)

    # ── Step 4.5: Enrich intent — match competitors + suggest refined keywords ─
    intent = intent_agent.enrich(intent, your_page, competitor_pages, keyword)

    # ── Step 5: Gap analysis ──────────────────────────────────────────────────
    step(5, "Computing keyword gaps...")
    gaps = gap_agent.run(serp, autocomplete, competitor_pages, your_page, keyword)

    elapsed = round(time.time() - t0, 2)
    step(6, f"Done in {elapsed}s — {len(gaps)} keyword gaps found")

    return AnalysisResult(
        keyword=keyword,
        your_url=your_url,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        intent=intent,
        serp=serp,
        autocomplete=autocomplete,
        competitor_pages=competitor_pages,
        your_page=your_page,
        gaps=gaps,
        data_sources=[
            "Google SERP organic titles + snippets (SerpAPI)",
            "People Also Ask (SerpAPI)",
            "Related Searches (SerpAPI)",
            "Google Autocomplete (live, unofficial)",
            "Competitor page content (requests + BeautifulSoup)",
        ],
    )


# ── CLI entry point ────────────────────────────────────────────────────────────

def _cli_progress(step_num, desc):
    icons = {1: "🔍", 2: "💡", 3: "🎯", 4: "🕷️", 5: "📊", 6: "✅"}
    icon = icons.get(step_num, "•")
    print(f"  [{step_num}/5] {icon}  {desc}")


def _print_summary(result: AnalysisResult):
    r = result
    intent = r.intent
    gaps   = r.gaps

    critical = [g for g in gaps if g.priority == "critical"]
    high     = [g for g in gaps if g.priority == "high"]
    medium   = [g for g in gaps if g.priority == "medium"]

    print()
    print("═" * 68)
    print("  KEYWORD GAP ANALYSIS")
    print("═" * 68)
    print(f"  Keyword   : {r.keyword}")
    print(f"  Your URL  : {r.your_url[:65]}")
    print(f"  Analyzed  : {r.analyzed_at}")
    print()
    print(f"  YOUR RANK : {intent.your_rank}")
    if not intent.match:
        print(f"  ⚠️  INTENT MISMATCH: {intent.warning}")
    print()

    print("  TOP 5 SERP RESULTS")
    print("  " + "─" * 60)
    for comp in r.competitor_pages:
        scraped_icon = "✓" if comp.scraped else "✗"
        print(f"  #{comp.rank}  {comp.title[:55]}")
        print(f"       {comp.url}")
        print(f"       words={comp.word_count}  scraped={scraped_icon}  keywords={len(comp.keywords)}")
    print()

    print(f"  KEYWORD GAPS  ({len(critical)} critical | {len(high)} high | {len(medium)} medium)")
    print("  " + "─" * 60)

    for label, group, icon in [("CRITICAL", critical, "🔴"), ("HIGH", high[:15], "🟠"), ("MEDIUM", medium[:10], "🟡")]:
        print(f"\n  {icon} {label}")
        if not group:
            print("    (none)")
        for g in group:
            src = " | ".join(dict.fromkeys(
                s.split(" #")[0].replace("(phrase)","").strip()
                for s in g.sources
            ))
            track_badge = "[product]" if g.track == "product_specific" else "[general]"
            print(f"    {track_badge} \"{g.keyword}\"  → {src}")

    print()
    print("  PAA QUESTIONS (add as H2 sections)")
    for q in r.serp.paa:
        print(f"    ❓ {q}")

    print()
    print("  RELATED SEARCHES (use as anchor text / section headers)")
    for s in r.serp.related_searches:
        print(f"    🔗 {s}")

    print()
    print("═" * 68)
    print(f"  TOTAL: {len(critical)} critical | {len(high)} high | {len(medium)} medium gaps")
    print("═" * 68)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print()
        print("Usage: python3 orchestrator.py \"<keyword>\" \"<your_url>\" [geo]")
        print()
        print("Examples:")
        print('  python3 orchestrator.py "interactive communications AEM" "https://experienceleague.adobe.com/..."')
        print('  python3 orchestrator.py "create pdf AEM Forms" "https://..." us')
        sys.exit(1)

    kw  = sys.argv[1]
    url = sys.argv[2]
    if len(sys.argv) < 4:
        print("\n  ERROR: geo (country code) is required. Example: us, uk, in\n")
        sys.exit(1)
    geo = sys.argv[3]

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   SEO Keyword Gap Analyzer — Agent Orchestrator  v2.0          ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    try:
        result = run_analysis(kw, url, geo, on_step=_cli_progress)
        _print_summary(result)

        fname = f"analysis_{kw.replace(' ', '_')}_{int(time.time())}.json"
        with open(fname, "w") as f:
            f.write(result.to_json())
        print(f"\n  Saved to: {fname}")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        sys.exit(1)
