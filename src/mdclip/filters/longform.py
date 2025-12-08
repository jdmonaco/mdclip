"""Longform journalism & magazine URL filter for mdclip.

This filter detects URLs from general interest magazines, literary
reviews, and longform journalism sites. Trusts domain alone for
known publications.

Usage in config:
    templates:
      - name: longform
        triggers:
          - "@longform"
        folder: Reference/Longform
"""

from ..builtin import BUILTIN_FILTERS, BuiltinFilter, MatchResult

# Lower threshold for longform - trust domains
LONGFORM_MATCH_THRESHOLD = 50


class LongformFilter(BuiltinFilter):
    """Filter for longform journalism and magazine URLs."""

    def __init__(self) -> None:
        super().__init__("longform")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for longform filter."""
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for longform sources."""
        result = super().match(url)
        is_match = result.score >= LONGFORM_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["longform"] = LongformFilter()
