"""
Shared dataclasses — the single source of truth for data shapes
passed between agents, orchestrator, and dashboard.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class SerpResult:
    organic: list          # raw organic_results from SerpAPI
    paa: list              # ["What is interactive communication?", ...]
    related_searches: list # ["AEM Forms Interactive Communication", ...]
    raw: dict = field(default_factory=dict, repr=False)  # full SerpAPI response


@dataclass
class AutocompleteResult:
    suggestions: list      # ["interactive communications aem", ...]


@dataclass
class IntentResult:
    match: bool
    warning: Optional[str]                     # None if match=True
    your_rank: str                             # "#1", "#3", "Not in top 10"
    matched_url: Optional[str]                 # exact or domain-level match
    serp_domains: list                         # top 3 domains shown in SERP
    intent_matched_competitor_ranks: list = field(default_factory=list)
    # Competitor ranks whose content is topically similar to your page
    suggested_keywords: list = field(default_factory=list)
    # Refined keyword variants derived from your page's headings that are
    # more likely to surface intent-matched SERP results


@dataclass
class PageData:
    url: str
    rank: object           # int or str
    title: str
    word_count: int
    h1: list
    h2: list
    h3: list
    keywords: list         # extracted terms from this page
    scraped: bool          # False if JS-blocked
    error: Optional[str] = None


@dataclass
class GapItem:
    keyword: str
    priority: str          # "critical" | "high" | "medium"
    signal_count: int
    sources: list          # ["People Also Ask", "SERP snippet #1", ...]
    track: str             # "general" | "product_specific"


@dataclass
class AnalysisResult:
    keyword: str
    your_url: str
    analyzed_at: str
    intent: IntentResult
    serp: SerpResult
    autocomplete: AutocompleteResult
    competitor_pages: list        # list[PageData]
    your_page: PageData
    gaps: list                    # list[GapItem] — flat, filter by priority/track
    data_sources: list

    def to_dict(self):
        return asdict(self)

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def gaps_by(self, priority=None, track=None):
        result = self.gaps
        if priority:
            result = [g for g in result if g["priority"] == priority] if isinstance(result[0], dict) else [g for g in result if g.priority == priority]
        if track:
            result = [g for g in result if g["track"] == track] if isinstance(result[0], dict) else [g for g in result if g.track == track]
        return result
