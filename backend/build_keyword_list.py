"""
Build a consolidated keyword recommendation list for the target article.
Merges gaps from all 4 reports into a clean, deduplicated table split by:
  - General keywords (broad SERP)
  - AEM-specific keywords (product-intent SERP)
"""

import json

ARTICLE_URL = "https://experienceleague.adobe.com/en/docs/experience-manager-65/content/forms/interactive-communications/introduction-interactive-communication-authoring"

# ── Load reports ──────────────────────────────────────────────────────────────
def load(path):
    with open(path) as f:
        return json.load(f)

ic_general  = load("report_interactive_communication_1774427148.json")
pdf_general = load("report_create_pdf_1774427161.json")
ic_aem      = load("report_interactive_communications_AEM_1774427282.json")
pdf_aem     = load("report_create_pdf_AEM_Forms_1774427305.json")

# ── Collect all gaps from a report ────────────────────────────────────────────
def collect_gaps(report):
    rows = []
    for priority in ["critical", "high", "medium"]:
        for g in report["gaps"].get(priority, []):
            rows.append({
                "keyword": g["kw"],
                "priority": priority,
                "in_competitors": g["in_competitors"],
                "total": g.get("total", 5),
            })
    return rows

def collect_paa(report):
    return [q for q in report.get("paa", [])]

def collect_related(report):
    return [r for r in report.get("related_searches", [])]

ic_gen_gaps   = collect_gaps(ic_general)
pdf_gen_gaps  = collect_gaps(pdf_general)
ic_aem_gaps   = collect_gaps(ic_aem)
pdf_aem_gaps  = collect_gaps(pdf_aem)

# ── Deduplicate within a group ────────────────────────────────────────────────
def dedup(gaps):
    seen = {}
    for g in gaps:
        k = g["keyword"].lower().strip()
        if k not in seen or (g["priority"] == "critical" or
           (g["priority"] == "high" and seen[k]["priority"] == "medium")):
            seen[k] = g
    # sort: critical > high > medium, then by in_competitors desc
    order = {"critical": 0, "high": 1, "medium": 2}
    return sorted(seen.values(), key=lambda x: (order[x["priority"]], -x["in_competitors"]))

ic_gen_dedup   = dedup(ic_gen_gaps)
pdf_gen_dedup  = dedup(pdf_gen_gaps)
ic_aem_dedup   = dedup(ic_aem_gaps)
pdf_aem_dedup  = dedup(pdf_aem_gaps)

# ── Print ─────────────────────────────────────────────────────────────────────
PRIORITY_LABELS = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
}

def print_section(title, gaps, paa=None, related=None):
    print()
    print("━" * 72)
    print(f"  {title}")
    print("━" * 72)
    print(f"  {'#':<4} {'PRIORITY':<14} {'KEYWORD':<35} {'IN COMPETITORS'}")
    print(f"  {'─'*4} {'─'*14} {'─'*35} {'─'*14}")
    for i, g in enumerate(gaps, 1):
        label = PRIORITY_LABELS[g["priority"]]
        print(f"  {i:<4} {label:<14} {g['keyword']:<35} {g['in_competitors']}/5 competitors")

    if paa:
        print()
        print(f"  PEOPLE ALSO ASK (add these as H2/H3 questions in your article):")
        for q in paa:
            print(f"    ❓ {q}")

    if related:
        print()
        print(f"  RELATED SEARCHES (use as section headers or anchor text):")
        for r in related:
            print(f"    🔗 {r}")

# ── GENERAL KEYWORDS ──────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════════════════════╗")
print("║   KEYWORD ADDITION LIST FOR YOUR ARTICLE                           ║")
print(f"║   URL: ...introduction-interactive-communication-authoring          ║")
print("╚══════════════════════════════════════════════════════════════════════╝")

print()
print("═" * 72)
print("  SECTION A — GENERAL KEYWORDS (broad audience, high search volume)")
print("  Source: Real Google SERP top-5 for general intent queries")
print("═" * 72)

# Merge IC + PDF general gaps, tag source
general_merged = {}
for g in ic_gen_dedup:
    k = g["keyword"].lower()
    if k not in general_merged:
        general_merged[k] = dict(g, source="interactive communication SERP")
for g in pdf_gen_dedup:
    k = g["keyword"].lower()
    if k not in general_merged:
        general_merged[k] = dict(g, source="create pdf SERP")
    else:
        # upgrade priority if higher
        order = {"critical": 0, "high": 1, "medium": 2}
        if order[g["priority"]] < order[general_merged[k]["priority"]]:
            general_merged[k]["priority"] = g["priority"]
            general_merged[k]["source"] += " + create pdf SERP"
        else:
            general_merged[k]["source"] += " + create pdf SERP"

order = {"critical": 0, "high": 1, "medium": 2}
gen_sorted = sorted(general_merged.values(), key=lambda x: (order[x["priority"]], -x["in_competitors"]))

print()
print(f"  {'#':<4} {'PRIORITY':<14} {'KEYWORD':<35} {'COMPETITORS':<14} SOURCE")
print(f"  {'─'*4} {'─'*14} {'─'*35} {'─'*14} {'─'*30}")
for i, g in enumerate(gen_sorted, 1):
    label = PRIORITY_LABELS[g["priority"]]
    print(f"  {i:<4} {label:<14} {g['keyword']:<35} {g['in_competitors']}/5          {g['source']}")

print()
print("  GENERAL PAA QUESTIONS (add as FAQ or H2 sections):")
all_gen_paa = list(dict.fromkeys(collect_paa(ic_general) + collect_paa(pdf_general)))
for q in all_gen_paa:
    print(f"    ❓ {q}")

print()
print("  GENERAL RELATED SEARCHES (use as internal link anchors or sub-sections):")
all_gen_related = list(dict.fromkeys(collect_related(ic_general) + collect_related(pdf_general)))
for r in all_gen_related:
    print(f"    🔗 {r}")

# ── AEM-SPECIFIC KEYWORDS ─────────────────────────────────────────────────────
print()
print("═" * 72)
print("  SECTION B — AEM-SPECIFIC KEYWORDS (product audience, intent-matched)")
print("  Source: Real Google SERP top-5 for AEM product queries")
print("═" * 72)

aem_merged = {}
for g in ic_aem_dedup:
    k = g["keyword"].lower()
    if k not in aem_merged:
        aem_merged[k] = dict(g, source="interactive communications AEM SERP")
for g in pdf_aem_dedup:
    k = g["keyword"].lower()
    if k not in aem_merged:
        aem_merged[k] = dict(g, source="create pdf AEM Forms SERP")
    else:
        order = {"critical": 0, "high": 1, "medium": 2}
        if order[g["priority"]] < order[aem_merged[k]["priority"]]:
            aem_merged[k]["priority"] = g["priority"]
        aem_merged[k]["source"] += " + create pdf AEM Forms SERP"

aem_sorted = sorted(aem_merged.values(), key=lambda x: (order[x["priority"]], -x["in_competitors"]))

print()
print(f"  {'#':<4} {'PRIORITY':<14} {'KEYWORD':<35} {'COMPETITORS':<14} SOURCE")
print(f"  {'─'*4} {'─'*14} {'─'*35} {'─'*14} {'─'*30}")
for i, g in enumerate(aem_sorted, 1):
    label = PRIORITY_LABELS[g["priority"]]
    print(f"  {i:<4} {label:<14} {g['keyword']:<35} {g['in_competitors']}/5          {g['source']}")

print()
print("  AEM-SPECIFIC PAA QUESTIONS:")
all_aem_paa = list(dict.fromkeys(collect_paa(ic_aem) + collect_paa(pdf_aem)))
for q in all_aem_paa:
    print(f"    ❓ {q}")

print()
print("  AEM-SPECIFIC RELATED SEARCHES:")
all_aem_related = list(dict.fromkeys(collect_related(ic_aem) + collect_related(pdf_aem)))
for r in all_aem_related:
    print(f"    🔗 {r}")

# ── COMBINED SUMMARY ──────────────────────────────────────────────────────────
print()
print("═" * 72)
print("  SUMMARY — TOTAL KEYWORDS TO ADD TO YOUR ARTICLE")
print("═" * 72)
c_gen = sum(1 for g in gen_sorted if g["priority"]=="critical")
h_gen = sum(1 for g in gen_sorted if g["priority"]=="high")
m_gen = sum(1 for g in gen_sorted if g["priority"]=="medium")
c_aem = sum(1 for g in aem_sorted if g["priority"]=="critical")
h_aem = sum(1 for g in aem_sorted if g["priority"]=="high")
m_aem = sum(1 for g in aem_sorted if g["priority"]=="medium")
print(f"  General keywords  : {c_gen} critical | {h_gen} high | {m_gen} medium = {len(gen_sorted)} total")
print(f"  AEM keywords      : {c_aem} critical | {h_aem} high | {m_aem} medium = {len(aem_sorted)} total")
print(f"  PAA questions     : {len(all_gen_paa)} general | {len(all_aem_paa)} AEM-specific")
print(f"  Related searches  : {len(all_gen_related)} general | {len(all_aem_related)} AEM-specific")
print()
print("  ACTION PLAN:")
print("  1. Add CRITICAL + HIGH AEM keywords first — they match your article's intent")
print("  2. Weave CRITICAL + HIGH general keywords into intro/meta description")
print("  3. Add 2-3 PAA questions as H2 sections with answers")
print("  4. Use Related Searches as internal link anchor text")
print("═" * 72)

# ── Save consolidated JSON ────────────────────────────────────────────────────
output = {
    "article_url": ARTICLE_URL,
    "general_keywords": gen_sorted,
    "aem_specific_keywords": aem_sorted,
    "general_paa": all_gen_paa,
    "aem_paa": all_aem_paa,
    "general_related_searches": all_gen_related,
    "aem_related_searches": all_aem_related,
}
with open("keyword_addition_list.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Full list saved to: keyword_addition_list.json")
