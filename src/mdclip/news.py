"""News source URL filter for mdclip.

This filter detects news article URLs with minimal path filtering,
trusting the domain alone for known news sources.

Usage in config:
    templates:
      - name: news
        triggers:
          - "@news"
        folder: Reference/News
"""

from .builtin import BUILTIN_FILTERS, BuiltinFilter, MatchResult

# Lower threshold for news - trust domains more
NEWS_MATCH_THRESHOLD = 50


class NewsFilter(BuiltinFilter):
    """Filter for news source URLs with minimal path filtering."""

    def __init__(self) -> None:
        super().__init__("news")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for news filter."""
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for news sources."""
        result = super().match(url)
        # Re-evaluate with lower threshold
        is_match = result.score >= NEWS_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["news"] = NewsFilter()
