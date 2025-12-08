"""Wiki & encyclopedia URL filter for mdclip.

This filter detects URLs from Wikipedia, Fandom, and other wiki/encyclopedia
sites. Trusts domain alone for known wiki platforms.

Usage in config:
    templates:
      - name: wiki
        triggers:
          - "@wiki"
        folder: Reference/Wiki
"""

from ..builtin import BUILTIN_FILTERS, BuiltinFilter, MatchResult

# Lower threshold for wiki - trust domains
WIKI_MATCH_THRESHOLD = 50


class WikiFilter(BuiltinFilter):
    """Filter for wiki and encyclopedia URLs."""

    def __init__(self) -> None:
        super().__init__("wiki")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for wiki filter."""
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for wiki sources."""
        result = super().match(url)
        is_match = result.score >= WIKI_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["wiki"] = WikiFilter()
