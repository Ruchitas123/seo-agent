"""
CrewAI orchestration for the SEO keyword gap pipeline.

Sequential crew: six specialist agents, each with one tool that runs the
existing deterministic agents (serp, autocomplete, intent, scrape, enrich, gap).

Requires an LLM API key unless using a local Ollama model — see backend README.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from crewai import Agent, Crew, LLM, Process, Task

from crew_tools import (
    AnalyzeIntentTool,
    ComputeKeywordGapsTool,
    EnrichIntentTool,
    FetchAutocompleteTool,
    FetchGoogleSerpTool,
    ScrapeCompetitorPagesTool,
    init_pipeline_state,
)
from models import AnalysisResult


def _default_llm() -> LLM:
    model = os.environ.get("CREW_LLM_MODEL", "gpt-4o-mini").strip()
    if model.startswith("ollama/"):
        return LLM(model=model, base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. CrewAI needs an LLM to coordinate agents. "
            "Add OPENAI_API_KEY to backend/.env, or set CREW_LLM_MODEL to an Ollama model "
            '(e.g. ollama/llama3.2) and run Ollama locally.'
        )
    return LLM(model=model)


def _build_crew(
    llm: LLM,
    on_step: Optional[Callable[[int, str], None]],
    verbose: bool,
    keyword: str,
) -> Crew:
    def step_cb(n: int, desc: str):
        def _cb(_output):
            if on_step:
                on_step(n, desc)

        return _cb

    serp_agent_ai = Agent(
        role="SERP Intelligence Specialist",
        goal="Retrieve live Google SERP data for the target keyword using your tool.",
        backstory=(
            "You specialize in Google SERP signals: organic listings, People Also Ask, "
            "and related searches. You never invent results—you always use the fetch tool."
        ),
        tools=[FetchGoogleSerpTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    autocomplete_agent_ai = Agent(
        role="Autocomplete Researcher",
        goal="Retrieve Google Autocomplete suggestions for the keyword via your tool.",
        backstory="You capture live search suggestions that reflect real user queries.",
        tools=[FetchAutocompleteTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    intent_agent_ai = Agent(
        role="Search Intent Analyst",
        goal="Determine how the user's URL fits the SERP using your tool.",
        backstory=(
            "You interpret whether the article matches ranking context for the query "
            "and where it appears in the top results."
        ),
        tools=[AnalyzeIntentTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    scraper_agent_ai = Agent(
        role="Web Content Extractor",
        goal="Scrape competitor pages and the user's article using your tool.",
        backstory=(
            "You extract headings and topical terms from HTML for gap analysis. "
            "You rely on the scraper tool for all fetching."
        ),
        tools=[ScrapeCompetitorPagesTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    enrich_agent_ai = Agent(
        role="Intent Enrichment Specialist",
        goal="Enrich intent signals after pages are scraped using your tool.",
        backstory="You refine intent metadata using scraped content overlap and headings.",
        tools=[EnrichIntentTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    gap_agent_ai = Agent(
        role="Keyword Gap Analyst",
        goal="Produce the final prioritized keyword gap list using your tool.",
        backstory=(
            "You synthesize SERP, autocomplete, and on-page signals into actionable "
            "gaps for content teams."
        ),
        tools=[ComputeKeywordGapsTool()],
        llm=llm,
        allow_delegation=False,
        verbose=verbose,
        max_iter=4,
    )

    task_serp = Task(
        description=(
            'Pipeline step 1 for keyword "{keyword}" (geo {geo}). '
            "You MUST call the tool `fetch_google_serp` exactly once. "
            "Do not fabricate SERP data. After the tool succeeds, reply with a one-line confirmation."
        ),
        expected_output="One line confirming SERP was fetched via the tool.",
        agent=serp_agent_ai,
        callback=step_cb(1, f'Fetching live Google SERP for "{keyword}"...'),
    )

    task_ac = Task(
        description=(
            'Pipeline step 2 for keyword "{keyword}". '
            "You MUST call `fetch_google_autocomplete` exactly once. "
            "Then confirm in one line."
        ),
        expected_output="One line confirming autocomplete was fetched.",
        agent=autocomplete_agent_ai,
        callback=step_cb(2, "Fetching Google Autocomplete suggestions..."),
    )

    task_intent = Task(
        description=(
            'Pipeline step 3. User article URL: {your_url}. '
            "SERP is already in the pipeline. Call `analyze_search_intent` exactly once. "
            "Confirm in one line."
        ),
        expected_output="One line confirming intent analysis.",
        agent=intent_agent_ai,
        callback=step_cb(3, "Detecting search intent and your article rank..."),
    )

    task_scrape = Task(
        description=(
            "Pipeline step 4. SERP is available. "
            "Call `scrape_competitor_and_article_pages` exactly once to scrape top competitors "
            "and the user's page. Confirm in one line."
        ),
        expected_output="One line confirming scrape completed.",
        agent=scraper_agent_ai,
        callback=step_cb(4, "Scraping competitor pages and your article..."),
    )

    task_enrich = Task(
        description=(
            "Pipeline step 5. Intent, competitor pages, and user page are in the pipeline. "
            "Call `enrich_intent_after_scrape` exactly once. Confirm in one line."
        ),
        expected_output="One line confirming intent enrichment.",
        agent=enrich_agent_ai,
        callback=None,
    )

    task_gaps = Task(
        description=(
            "Pipeline step 6 (final). All prior data is in the pipeline. "
            "Call `compute_keyword_gaps` exactly once. Confirm how many gaps were found."
        ),
        expected_output="One line stating keyword gap count from the tool.",
        agent=gap_agent_ai,
        callback=step_cb(5, "Computing keyword gaps..."),
    )

    return Crew(
        agents=[
            serp_agent_ai,
            autocomplete_agent_ai,
            intent_agent_ai,
            scraper_agent_ai,
            enrich_agent_ai,
            gap_agent_ai,
        ],
        tasks=[task_serp, task_ac, task_intent, task_scrape, task_enrich, task_gaps],
        process=Process.sequential,
        verbose=verbose,
    )


def run_analysis_with_crew(
    keyword: str,
    your_url: str,
    geo: str,
    on_step: Optional[Callable[[int, str], None]] = None,
) -> AnalysisResult:
    init_pipeline_state(keyword, your_url, geo)
    llm = _default_llm()
    verbose = os.environ.get("CREW_VERBOSE", "").lower() in ("1", "true", "yes")
    crew = _build_crew(llm, on_step, verbose, keyword)

    t0 = time.time()
    crew.kickoff(inputs={"keyword": keyword, "geo": geo, "your_url": your_url})

    from crew_tools import PIPELINE_STATE as s

    required = ("serp", "autocomplete", "intent", "competitor_pages", "your_page", "gaps")
    missing = [k for k in required if k not in s]
    if missing:
        raise RuntimeError(
            "Crew finished but pipeline state is incomplete (missing: "
            + ", ".join(missing)
            + "). Ensure each agent invoked its tool."
        )

    elapsed = round(time.time() - t0, 2)
    if on_step:
        on_step(6, f"Done in {elapsed}s — {len(s['gaps'])} keyword gaps found")

    return AnalysisResult(
        keyword=keyword,
        your_url=your_url,
        analyzed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        intent=s["intent"],
        serp=s["serp"],
        autocomplete=s["autocomplete"],
        competitor_pages=s["competitor_pages"],
        your_page=s["your_page"],
        gaps=s["gaps"],
        data_sources=[
            "Google SERP organic titles + snippets (SerpAPI)",
            "People Also Ask (SerpAPI)",
            "Related Searches (SerpAPI)",
            "Google Autocomplete (live, unofficial)",
            "Competitor page content (requests + BeautifulSoup)",
            "Orchestration: CrewAI sequential crew + tools",
        ],
    )
