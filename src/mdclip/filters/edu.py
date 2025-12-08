"""Educational content URL filter for mdclip.

This filter detects URLs from educational platforms and .edu domains.
Matches .edu TLD or known educational platforms.

Usage in config:
    templates:
      - name: education
        triggers:
          - "@edu"
        folder: Reference/Education
"""

from ..builtin import BUILTIN_FILTERS, SCORE_REGEX_MATCH, BuiltinFilter, MatchResult

# Lower threshold for edu - trust domains and .edu TLD
EDU_MATCH_THRESHOLD = 50


class EduFilter(BuiltinFilter):
    """Filter for educational content URLs."""

    def __init__(self) -> None:
        super().__init__("edu")

    def _check_special_patterns(self, url: str) -> int:
        """Check for .edu TLD pattern."""
        edu_regex = self.data.regexes.get("edu_tld")
        if edu_regex and edu_regex.search(url):
            return SCORE_REGEX_MATCH
        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for edu sources."""
        result = super().match(url)
        is_match = result.score >= EDU_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["edu"] = EduFilter()
