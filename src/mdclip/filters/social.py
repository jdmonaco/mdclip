"""Social media & discussion platform URL filter for mdclip.

This filter detects URLs from social media platforms, forums,
and discussion sites. Trusts domain alone for known sources.

Usage in config:
    templates:
      - name: social
        triggers:
          - "@social"
        folder: Reference/Social
"""

from ..builtin import BUILTIN_FILTERS, BuiltinFilter, MatchResult

# Lower threshold for social - trust domains
SOCIAL_MATCH_THRESHOLD = 50


class SocialFilter(BuiltinFilter):
    """Filter for social media and discussion platform URLs."""

    def __init__(self) -> None:
        super().__init__("social")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for social filter."""
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for social sources."""
        result = super().match(url)
        # Re-evaluate with lower threshold
        is_match = result.score >= SOCIAL_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["social"] = SocialFilter()
