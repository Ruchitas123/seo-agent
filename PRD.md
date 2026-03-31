# PRD: AI-Powered SEO + GEO Keyword Gap Analyzer
**Version:** 2.0
**Last Updated:** 2026-03-26
**Framework:** CREATE (Context · Relationship · Example · Application · Teaching · Experience)
**Engineering principles:** 8 Lessons from Building AI Agents (Khushwant Sehgal)

---

## CONTEXT

### Problem Statement
Content teams publish articles that fail to rank on Google because they miss keywords that Google's own SERP signals — PAA questions, related searches, autocomplete, and competitor snippets — already surface as relevant. The gap between what an article covers and what Google considers relevant is the **keyword gap**.

Existing tools (Ahrefs, SEMrush) solve this but are expensive ($100–$400/mo). Free tools either return wrong data (DuckDuckGo ≠ Google results), tokenize text without semantic understanding, or skip SERP signals entirely.

### What We Learned Building v1
| Attempt | What went wrong | Lesson |
|---|---|---|
| DuckDuckGo SERP | Returned wrong results — Wikipedia/Genially for "interactive communication" vs real Google (Prezent.ai, Avocor) | DuckDuckGo ≠ Google. Must use SerpAPI for real Google data |
| Tokenizing SERP snippets | Split sentences into words — not real keyword research | Keywords from tokenization ≠ keywords people search for |
| Scraping competitor pages | JS-rendered sites (Canva, Indeed, Medium, Reddit) return 0 words | Need headless browser (Playwright) or fallback strategy |
| Generic vs product keywords | "interactive communication" → Google ranks theory articles, not AEM docs | Intent mismatch must be detected before analysis |
| Keyword priority | Used competitor prevalence count (2/5, 3/5) | Priority must be based on **source quality**: SERP signal > page content |

### Real Keyword Sources (validated)
| Source | Signal quality | API | Cost |
|---|---|---|---|
| PAA questions | ★★★★★ — Google's own intent clusters | SerpAPI | $0 (free tier 250/mo) |
| Related Searches | ★★★★★ — Google's own keyword clusters | SerpAPI | $0 (free tier) |
| Google Autocomplete | ★★★★☆ — live search suggestions | Unofficial (free) | Free |
| Organic titles + snippets | ★★★☆☆ — Google-highlighted terms | SerpAPI | $0 (free tier) |
| Competitor page content | ★★☆☆☆ — supplemental depth only | requests + BeautifulSoup | Free |
| Keywords a URL ranks for | ★★★★★ — most accurate gap signal | DataForSEO | ~$0.003/call |

**What is NOT a valid keyword source:**
- Tokenized words from snippet sentences (these are sentence words, not search queries)
- DuckDuckGo or Bing SERP (not Google intent)
- Hardcoded GEO pattern lists

---

## RELATIONSHIP

### System Architecture

```
User Input
  └─ target keyword + article URL + (optional) geo
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  LAYER 1: SERP Intelligence (Real Google signals)   │
  │                                                     │
  │  SerpAPI ──► organic results (top 10)              │
  │           ├─► PAA questions          ← real keywords│
  │           ├─► Related Searches       ← real keywords│
  │           └─► Organic snippets       ← context only │
  │                                                     │
  │  Google Autocomplete ──► live suggestions           │
  └─────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  LAYER 2: Competitor Intelligence                   │
  │                                                     │
  │  Scrape top 5 URLs ──► extract h1/h2/h3 + body     │
  │  (fallback: Playwright for JS-rendered pages)       │
  │                                                     │
  │  DataForSEO (optional) ──► keywords each URL ranks  │
  └─────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  LAYER 3: Your Article Analysis                     │
  │                                                     │
  │  Scrape article URL ──► extract all terms           │
  │  Detect intent match/mismatch vs SERP               │
  └─────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  LAYER 4: Gap Computation + Priority Scoring        │
  │                                                     │
  │  CRITICAL = in PAA/Related Searches + page content  │
  │  HIGH     = in PAA/Related Searches only            │
  │  MEDIUM   = in competitor pages only (3+ mentions)  │
  │                                                     │
  │  GEO layer = locale-specific keyword variants       │
  └─────────────────────────────────────────────────────┘
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  OUTPUT                                             │
  │  • Your rank in SERP                                │
  │  • Top 5 SERP URLs + their keywords                 │
  │  • Keyword gap list (critical/high/medium)          │
  │  • General keywords + Product-specific keywords     │
  │  • PAA questions to add as article sections         │
  │  • Related searches to use as anchor text           │
  │  • Intent match/mismatch warning                    │
  └─────────────────────────────────────────────────────┘
```

### Keyword Dual-Track Output
Every analysis produces **two keyword lists**:
1. **General keywords** — broad audience, high search volume (e.g. "interactive communication")
2. **Product-specific keywords** — intent-matched, rankable (e.g. "interactive communications AEM")

Both lists are always generated in one run, because:
- General keywords inform meta descriptions and intro paragraphs
- Product-specific keywords inform body content and section headings

### Intent Mismatch Detection
Before gap analysis, detect if the article's topic matches SERP intent:
- Fetch top 3 SERP URLs
- Compare domains to user's domain
- If 0/3 are on the same domain or product space → **INTENT MISMATCH WARNING**
- Example: "create pdf" → Google ranks Canva/ilovepdf, not AEM docs → warn the user

---

## EXAMPLE

### Validated Test Case
**Article:** `experienceleague.adobe.com/.../introduction-interactive-communication-authoring`
**Keywords tested:** "interactive communication", "create pdf", "interactive communications AEM", "create pdf AEM Forms"

**Findings:**
| Keyword | Your rank | Intent match | Actionable? |
|---|---|---|---|
| interactive communication | Not in top 10 | ✗ Google ranks theory articles | ✗ No — wrong intent |
| create pdf | Not in top 10 | ✗ Google ranks web tools (Canva, ilovepdf) | ✗ No — wrong intent |
| interactive communications AEM | #1 (different page, same domain) | ✓ Google ranks AEM docs | ✓ Yes |
| create pdf AEM Forms | #1 (different page, same domain) | ✓ Google ranks AEM tutorials | ✓ Yes |

**Top gaps found (product keywords, sourced from real SERP signals):**
- `aem forms`, `interactive communications`, `data model`, `document fragments`, `correspondences`, `personalized`, `output service`, `pdfg`, `generate pdf`, `adaptive form`, `pdf forms designer`

**Source of each gap:** PAA questions, Related Searches, SERP snippets, competitor page content — NOT tokenized text

---

## APPLICATION

### MVP Scope (v1 → v2 upgrade)

#### What v1 did (wrong)
- Used DuckDuckGo instead of Google SERP
- Extracted keywords by tokenizing SERP snippet sentences
- Reported generic tokens ("like", "time", "feel") as keywords
- No intent mismatch detection
- Single keyword list (no general vs product split)

#### What v2 must do (correct)
- **Real Google SERP** via SerpAPI for every analysis
- **PAA + Related Searches used as-is** — these are already keyword phrases, not tokenized
- **Google Autocomplete** for live search suggestions
- **Intent mismatch detection** before analysis begins
- **Dual-track output**: general keywords + product-specific keywords
- **Keyword source labeling**: every gap must show where it came from
- **DataForSEO** (optional, pay-per-call) for keywords a URL actually ranks for

#### Out of scope (Post-MVP)
- Article rewriting / content generation
- Search volume / CPC data (DataForSEO add-on)
- Backlink analysis
- GEO-specific keyword generation (hardcoded patterns removed — must come from SERP)

### Free-First Tooling Stack
| Tool | Purpose | Cost |
|---|---|---|
| SerpAPI | Real Google SERP, PAA, related searches | Free (250/mo), $50/mo paid |
| Google Autocomplete | Live search suggestions | Free (unofficial) |
| requests + BeautifulSoup | Scrape static pages | Free |
| Playwright (future) | Scrape JS-rendered pages (Canva, Medium, Reddit) | Free |
| DataForSEO Keywords API | Keywords a URL ranks for | ~$0.003/call, on-demand only |

**Cost target:** $0 for standard runs, <$0.01 for DataForSEO-enriched runs

---

## TEACHING

### Engineering Principles Applied (8 Lessons)

**1. Frontend/backend separation**
- `serp_keyword_report.py` = backend pipeline only
- Output is structured JSON → consumable by any UI (CLI, web app, Slack bot)

**2. Open standards (MCP, A2A)**
- Keyword gap output follows a stable JSON schema
- Can be exposed as an MCP tool for AI agent consumption

**3. LLM-agnostic design**
- No LLM in the keyword extraction pipeline — pure data pipeline
- LLM can be added later as a layer to interpret gaps and draft content additions
- Not locked to any model

**4. Analytics from day one**
- Every run logs: keyword, URL, timestamp, data sources used, latency
- `analyzed_at`, `latency_seconds`, `tooling_used` fields in every output JSON

**5. Documentation as product feature**
- Every keyword gap includes `sources` field (which Google signal triggered it)
- Priority logic is documented in output: CRITICAL/HIGH/MEDIUM definitions shown in every report

**6. Living OpenAPI spec**
- JSON output schema is stable and versioned
- `analysis_id`, `keyword`, `your_url`, `your_rank`, `gaps.critical/high/medium` are fixed fields

**7. Nudge Architecture**
- Intent mismatch warning shown before gap list — nudges user toward the right keyword before they act on wrong gaps
- Autocomplete suggestions shown even if all are gaps — nudges user to see real search demand

**8. Adoption over demos**
- CLI-first: `echo "keyword\nurl" | python3 serp_keyword_report.py`
- No setup required beyond `pip install requests beautifulsoup4`
- SerpAPI key is the only external dependency

---

## EXPERIENCE

### User Flow
```
1. User provides: keyword + article URL
2. System detects: intent match or mismatch → warns if mismatch
3. System fetches: live Google SERP (PAA, related searches, autocomplete)
4. System scrapes: top 5 competitor pages
5. System outputs:
     - Your rank in SERP
     - Top 5 SERP URLs with their keywords
     - Keyword gap list split by:
         • General keywords (broad)
         • Product-specific keywords (intent-matched)
     - PAA questions to add as H2 sections
     - Related searches to use as anchor text
     - Source label for every keyword
6. JSON report saved to disk
```

### Output Contract (JSON Schema)
```json
{
  "keyword": "string",
  "your_url": "string",
  "your_rank": "string",
  "intent_match": "boolean",
  "intent_warning": "string | null",
  "analyzed_at": "ISO8601",
  "data_sources": ["string"],
  "top5_serp": [
    { "rank": "int", "title": "string", "url": "string",
      "word_count": "int", "keywords": ["string"] }
  ],
  "autocomplete": ["string"],
  "paa": ["string"],
  "related_searches": ["string"],
  "your_article": { "word_count": "int", "h1": [], "h2": [] },
  "keyword_gaps": {
    "general": {
      "critical": [{ "keyword": "string", "sources": ["string"] }],
      "high":     [{ "keyword": "string", "sources": ["string"] }],
      "medium":   [{ "keyword": "string", "sources": ["string"] }]
    },
    "product_specific": {
      "critical": [...],
      "high":     [...],
      "medium":   [...]
    }
  }
}
```

### Known Limitations
| Limitation | Impact | Fix |
|---|---|---|
| JS-rendered pages (Canva, Indeed, Reddit, Medium) can't be scraped | Missing competitor keyword data | Add Playwright headless scraper |
| SerpAPI free tier: 250 searches/mo | Rate limit for high-volume use | Cache results per keyword (TTL: 24hr) |
| Google Autocomplete blocks heavy usage | Suggestion data may be empty | Retry with delay; treat as optional signal |
| PAA/related searches vary by location | Results may differ from user's actual target geo | Add `gl` param to SerpAPI call per geo |
| No real search volume data | Can't rank keywords by actual traffic potential | Add DataForSEO volume lookup for critical gaps only |

---

## ROADMAP

### v2.0 (Current — this PRD)
- [x] Real Google SERP via SerpAPI
- [x] PAA + Related Searches as keyword source
- [x] Google Autocomplete integration
- [x] Dual-track: general + product-specific keywords
- [x] Intent mismatch detection
- [x] Keyword source labeling
- [x] Your URL rank in SERP
- [x] Top 5 SERP URLs with scraped keywords
- [x] JSON output with stable schema

### v2.1 (Next)
- [ ] Playwright fallback for JS-rendered pages
- [ ] 24hr result caching to preserve SerpAPI quota
- [ ] GEO parameter: pass target country to SerpAPI (`gl` param)
- [ ] DataForSEO integration: competitor URL → keywords it ranks for

### v3.0 (Post-MVP)
- [ ] LLM layer: interpret gaps and draft content additions
- [ ] Web UI: keyword gap dashboard
- [ ] MCP tool: expose as agent-callable tool
- [ ] Batch mode: analyze multiple URLs + keywords in one run
- [ ] Article rewrite suggestions based on gap list
