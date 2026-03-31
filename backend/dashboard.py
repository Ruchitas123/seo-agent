"""
SEO Keyword Gap Analyzer — Streamlit Dashboard
-----------------------------------------------
Run: streamlit run dashboard.py
"""

import json
import time
from dataclasses import asdict

import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SEO Keyword Gap Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .priority-critical { color: #e53e3e; font-weight: 700; }
    .priority-high      { color: #dd6b20; font-weight: 600; }
    .priority-medium    { color: #d69e2e; font-weight: 500; }
    .track-product      { background: #ebf8ff; border-radius: 4px; padding: 2px 6px;
                          color: #2b6cb0; font-size: 0.75rem; font-weight: 600; }
    .track-general      { background: #f0fff4; border-radius: 4px; padding: 2px 6px;
                          color: #276749; font-size: 0.75rem; font-weight: 600; }
    .intent-warning     { background: #fff5f5; border-left: 4px solid #e53e3e;
                          padding: 12px 16px; border-radius: 4px; margin: 8px 0; }
    .intent-ok          { background: #f0fff4; border-left: 4px solid #38a169;
                          padding: 12px 16px; border-radius: 4px; margin: 8px 0; }
    .source-tag         { font-size: 0.72rem; color: #718096; }
    .serp-url           { font-size: 0.8rem; color: #3182ce; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 SEO Keyword Gap Analyzer")
    st.caption("v2.0 — Powered by real Google SERP")
    st.divider()

    keyword  = st.text_input("Target Keyword", placeholder="e.g. interactive communications AEM")
    your_url = st.text_input("Your Article URL", placeholder="https://...")
    geo      = st.text_input("Target Geo", value="us", help="2-letter country code: us, uk, in, au")

    run_btn = st.button("▶  Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.caption("**Data sources used:**")
    st.caption("• Google SERP via SerpAPI")
    st.caption("• People Also Ask")
    st.caption("• Related Searches")
    st.caption("• Google Autocomplete")
    st.caption("• Competitor page scraping")

# ── Session state ─────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "error" not in st.session_state:
    st.session_state.error = None

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:
    if not keyword.strip() or not your_url.strip():
        st.sidebar.error("Both keyword and URL are required.")
    else:
        st.session_state.result = None
        st.session_state.error  = None

        step_labels = {
            1: "Fetching live Google SERP...",
            2: "Fetching Google Autocomplete...",
            3: "Detecting search intent...",
            4: "Scraping competitor pages...",
            5: "Computing keyword gaps...",
            6: "Done!",
        }

        progress_bar = st.progress(0, text="Starting pipeline...")
        status_msgs  = []

        def on_step(n, desc):
            pct = min(int((n / 6) * 100), 100)
            progress_bar.progress(pct, text=f"Step {min(n,5)}/5 — {desc}")
            status_msgs.append(f"✓ Step {min(n,5)}: {desc}")

        try:
            from orchestrator import run_analysis
            result = run_analysis(keyword.strip(), your_url.strip(), geo.strip() or "us", on_step=on_step)
            st.session_state.result = result
            progress_bar.progress(100, text="Analysis complete!")
            time.sleep(0.3)
            progress_bar.empty()
        except Exception as e:
            progress_bar.empty()
            st.session_state.error = str(e)

# ── Error display ─────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(f"Pipeline error: {st.session_state.error}")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.result:
    r      = st.session_state.result
    intent = r.intent
    gaps   = r.gaps

    critical_gaps = [g for g in gaps if g.priority == "critical"]
    high_gaps     = [g for g in gaps if g.priority == "high"]
    medium_gaps   = [g for g in gaps if g.priority == "medium"]

    prod_gaps = [g for g in gaps if g.track == "product_specific"]
    gen_gaps  = [g for g in gaps if g.track == "general"]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🎯 Keyword Gaps",
        "🔎 SERP Signals",
        "🕷️ Competitor Breakdown",
        "📄 Raw JSON",
    ])

    # ── TAB 1: Overview ───────────────────────────────────────────────────────
    with tab1:
        st.subheader("Analysis Overview")

        # Intent banner
        if not intent.match:
            st.markdown(
                f'<div class="intent-warning">⚠️ <strong>Intent Mismatch Detected</strong><br>{intent.warning}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="intent-ok">✅ <strong>Intent Match</strong> — Your domain appears in the top 10 for this keyword.</div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # Metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Your Rank", intent.your_rank)
        col2.metric("🔴 Critical Gaps", len(critical_gaps))
        col3.metric("🟠 High Gaps",     len(high_gaps))
        col4.metric("🟡 Medium Gaps",   len(medium_gaps))
        col5.metric("Total Gaps",       len(gaps))

        st.divider()

        # Top 5 SERP table
        st.subheader("Top 5 SERP Results")
        for comp in r.competitor_pages:
            scraped_badge = "✅ scraped" if comp.scraped else "❌ JS-blocked"
            with st.expander(f"#{comp.rank} — {comp.title}", expanded=False):
                st.markdown(f'<span class="serp-url">{comp.url}</span>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Words", comp.word_count)
                c2.metric("Keywords found", len(comp.keywords))
                c3.metric("Status", scraped_badge)
                if comp.h2:
                    st.caption("**H2 sections:** " + " · ".join(comp.h2[:5]))
                if comp.error:
                    st.caption(f"Error: {comp.error}")

        st.divider()
        st.subheader("Your Article")
        yp = r.your_page
        c1, c2, c3 = st.columns(3)
        c1.metric("Words", yp.word_count)
        c2.metric("Keywords in article", len(yp.keywords))
        c3.metric("Scraped", "✅" if yp.scraped else "❌")
        if yp.h1:
            st.caption("**H1:** " + " / ".join(yp.h1[:2]))
        if yp.h2:
            st.caption("**H2 sections:** " + " · ".join(yp.h2[:6]))

    # ── TAB 2: Keyword Gaps ───────────────────────────────────────────────────
    with tab2:
        st.subheader("Keyword Gap List")

        col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
        with col_f1:
            priority_filter = st.multiselect(
                "Priority",
                ["critical", "high", "medium"],
                default=["critical", "high"],
            )
        with col_f2:
            track_filter = st.radio(
                "Track",
                ["All", "Product Specific", "General"],
                horizontal=True,
            )
        with col_f3:
            search_term = st.text_input("Search keywords", placeholder="filter by keyword...")

        # Apply filters
        filtered = gaps
        if priority_filter:
            filtered = [g for g in filtered if g.priority in priority_filter]
        if track_filter == "Product Specific":
            filtered = [g for g in filtered if g.track == "product_specific"]
        elif track_filter == "General":
            filtered = [g for g in filtered if g.track == "general"]
        if search_term:
            filtered = [g for g in filtered if search_term.lower() in g.keyword.lower()]

        st.caption(f"Showing **{len(filtered)}** gaps")
        st.divider()

        PRIORITY_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡"}
        PRIORITY_COLORS = {"critical": "#e53e3e", "high": "#dd6b20", "medium": "#d69e2e"}

        # Render as cards
        for g in filtered:
            icon       = PRIORITY_ICONS[g.priority]
            color      = PRIORITY_COLORS[g.priority]
            track_html = (
                '<span class="track-product">product</span>'
                if g.track == "product_specific"
                else '<span class="track-general">general</span>'
            )
            src_short = " · ".join(dict.fromkeys(
                s.split(" #")[0].replace("(phrase)","").replace("(question)","").strip()
                for s in g.sources
            ))
            st.markdown(
                f'{icon} <strong style="color:{color}; font-size:1rem">{g.keyword}</strong> '
                f'&nbsp;{track_html}'
                f'<br><span class="source-tag">Sources: {src_short} &nbsp;|&nbsp; '
                f'Signal score: {g.signal_count}</span>',
                unsafe_allow_html=True,
            )
            st.divider()

    # ── TAB 3: SERP Signals ───────────────────────────────────────────────────
    with tab3:
        st.subheader("Live Google SERP Signals")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 💬 People Also Ask")
            st.caption("Real user intent questions — add as H2 sections in your article")
            for q in r.serp.paa:
                in_article = any(w in r.your_page.keywords for w in q.lower().split() if len(w) > 4)
                badge = "✅" if in_article else "❌ GAP"
                st.markdown(f"{badge} &nbsp; {q}")
            if not r.serp.paa:
                st.caption("No PAA questions found for this keyword.")

            st.divider()
            st.markdown("#### 🔗 Related Searches")
            st.caption("Google's own keyword clusters — use as anchor text or section headers")
            for s in r.serp.related_searches:
                in_article = any(w in r.your_page.keywords for w in s.lower().split() if len(w) > 4)
                badge = "✅" if in_article else "❌ GAP"
                st.markdown(f"{badge} &nbsp; {s}")

        with c2:
            st.markdown("#### 🔤 Google Autocomplete")
            st.caption("Live suggestions as users type this keyword")
            for s in r.autocomplete.suggestions:
                in_article = s.lower() in r.your_page.keywords
                badge = "✅" if in_article else "❌ GAP"
                st.markdown(f"{badge} &nbsp; {s}")
            if not r.autocomplete.suggestions:
                st.caption("No autocomplete suggestions returned (may be rate-limited).")

            st.divider()
            st.markdown("#### 🏆 Organic Snippets (top 5)")
            st.caption("What Google highlights for each result")
            for res in r.serp.organic[:5]:
                st.markdown(f"**#{res.get('position')}** {res.get('title','')}")
                st.caption(res.get("snippet","(no snippet)")[:200])

    # ── TAB 4: Competitor Breakdown ───────────────────────────────────────────
    with tab4:
        st.subheader("Per-Competitor Keyword Breakdown")
        st.caption("Keywords each competitor uses that are missing from your article")

        your_kws = set(r.your_page.keywords)

        for comp in r.competitor_pages:
            with st.expander(
                f"#{comp.rank} — {comp.title[:60]} ({'✅ scraped' if comp.scraped else '❌ JS-blocked'})",
                expanded=False,
            ):
                if not comp.scraped:
                    st.warning(f"Could not scrape this page — it's JS-rendered. URL: {comp.url}")
                    continue

                missing = [k for k in comp.keywords if k not in your_kws]
                present = [k for k in comp.keywords if k in your_kws]

                st.markdown(f'<span class="serp-url">{comp.url}</span>', unsafe_allow_html=True)
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Words", comp.word_count)
                cc2.metric(f"Missing from your article", len(missing))
                cc3.metric(f"Already in your article", len(present))

                if missing:
                    st.markdown("**Keywords missing from your article:**")
                    # Show as tag cloud
                    tags = "  ".join(f"`{k}`" for k in missing[:40])
                    st.markdown(tags)

                if present:
                    with st.expander("Keywords already in your article"):
                        st.markdown("  ".join(f"`{k}`" for k in present[:30]))

    # ── TAB 5: Raw JSON ───────────────────────────────────────────────────────
    with tab5:
        st.subheader("Full Analysis JSON")

        json_str = r.to_json()

        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name=f"gap_analysis_{r.keyword.replace(' ','_')}_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True,
        )

        st.code(json_str[:8000] + ("\n... (truncated)" if len(json_str) > 8000 else ""), language="json")

# ── Empty state ───────────────────────────────────────────────────────────────
else:
    if not run_btn:
        st.markdown("""
        ## Welcome to the SEO Keyword Gap Analyzer 🔍

        Enter a **keyword** and your **article URL** in the sidebar, then click **Run Analysis**.

        ### What this tool does:
        1. **Fetches real Google SERP** for your keyword (via SerpAPI)
        2. **Extracts keyword signals** from PAA, Related Searches, Autocomplete — not tokenized text
        3. **Detects intent mismatch** — warns if Google ranks a different audience than your article
        4. **Scrapes top 5 competitor pages** for depth
        5. **Reports keyword gaps** with source labels and priority levels

        ### Keyword Gap Priority:
        | Priority | Meaning |
        |---|---|
        | 🔴 Critical | In Google PAA/Related Searches **AND** competitor pages |
        | 🟠 High | In Google SERP signals (PAA, related, autocomplete) |
        | 🟡 Medium | In competitor page content only (3+ mentions) |

        ### Keyword Tracks:
        - **Product Specific** — contains domain/product tokens from your keyword (e.g. "aem", "adobe")
        - **General** — broad terms relevant to the topic
        """)
