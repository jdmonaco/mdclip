"""Science & technology publication URL filter for mdclip.

This filter detects URLs from popular science and technology magazines,
blogs, and industry publications. Trusts domain alone for known sources.

Usage in config:
    templates:
      - name: scitech
        triggers:
          - "@scitech"
        folder: Reference/SciTech
"""

from ..builtin import BUILTIN_FILTERS, BuiltinFilter, MatchResult

# Lower threshold for scitech - trust domains more
SCITECH_MATCH_THRESHOLD = 50


class ScitechFilter(BuiltinFilter):
    """Filter for science & technology publication URLs."""

    def __init__(self) -> None:
        super().__init__("scitech")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for scitech filter."""
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for scitech sources."""
        result = super().match(url)
        # Re-evaluate with lower threshold
        is_match = result.score >= SCITECH_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["scitech"] = ScitechFilter()
