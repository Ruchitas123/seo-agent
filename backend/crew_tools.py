"""
CrewAI tools — thin wrappers around existing agent modules.

Pipeline state lives in ``PIPELINE_STATE`` (reset per run). Each tool mutates
state so deterministic Python logic is unchanged; CrewAI agents coordinate
when to invoke tools via the LLM.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool

from agents import autocomplete_agent, gap_agent, intent_agent, scraper_agent, serp_agent

PIPELINE_STATE: dict[str, Any] = {}


def reset_pipeline_state() -> None:
    PIPELINE_STATE.clear()


def init_pipeline_state(keyword: str, your_url: str, geo: str) -> None:
    reset_pipeline_state()
    PIPELINE_STATE["keyword"] = keyword
    PIPELINE_STATE["your_url"] = your_url
    PIPELINE_STATE["geo"] = geo


class FetchGoogleSerpTool(BaseTool):
    name: str = "fetch_google_serp"
    description: str = (
        "Fetches live Google SERP via SerpAPI: organic results, People Also Ask, "
        "and related searches for the current analysis keyword and geo. "
        "You must call this tool exactly once for this task."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        s["serp"] = serp_agent.run(s["keyword"], s["geo"])
        return "SERP data retrieved (organic, PAA, related searches)."


class FetchAutocompleteTool(BaseTool):
    name: str = "fetch_google_autocomplete"
    description: str = (
        "Fetches Google Autocomplete suggestions for the current keyword. "
        "Call exactly once for this task."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        s["autocomplete"] = autocomplete_agent.run(s["keyword"])
        return "Autocomplete suggestions retrieved."


class AnalyzeIntentTool(BaseTool):
    name: str = "analyze_search_intent"
    description: str = (
        "Compares the user's article URL to the SERP: rank, domain match, and "
        "intent/ranking-gap signal. Requires SERP already fetched. Call once."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        s["intent"] = intent_agent.run(s["your_url"], s["serp"])
        return "Intent and rank analysis complete."


class ScrapeCompetitorPagesTool(BaseTool):
    name: str = "scrape_competitor_and_article_pages"
    description: str = (
        "Scrapes top organic competitor pages and the user's article; extracts "
        "headings and keywords. Requires SERP in state. Call once."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        serp = s["serp"]
        urls_with_meta = [
            {"url": r.get("link", ""), "rank": r.get("position", "?"), "title": r.get("title", "")}
            for r in serp.organic[:5]
            if r.get("link")
        ]
        comp, yours = scraper_agent.run(urls_with_meta, s["your_url"])
        s["competitor_pages"] = comp
        s["your_page"] = yours
        return f"Scraped {len(comp)} competitor pages and the user's article."


class EnrichIntentTool(BaseTool):
    name: str = "enrich_intent_after_scrape"
    description: str = (
        "After scraping, enriches intent with intent-matched competitor ranks and "
        "suggested keyword variants from headings. Call once after scrape."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        s["intent"] = intent_agent.enrich(
            s["intent"], s["your_page"], s["competitor_pages"], s["keyword"]
        )
        return "Intent enrichment complete (matched competitors, suggested keywords)."


class ComputeKeywordGapsTool(BaseTool):
    name: str = "compute_keyword_gaps"
    description: str = (
        "Computes prioritized keyword gaps (critical/high/medium) from SERP, "
        "autocomplete, and scraped content. Call once as the final pipeline step."
    )

    def _run(self) -> str:
        s = PIPELINE_STATE
        s["gaps"] = gap_agent.run(
            s["serp"],
            s["autocomplete"],
            s["competitor_pages"],
            s["your_page"],
            s["keyword"],
        )
        return f"Identified {len(s['gaps'])} keyword gaps."
