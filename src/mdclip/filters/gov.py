"""Government & official URL filter for mdclip.

This filter detects URLs from government sites using .gov/.mil TLDs
and known government domains.

Usage in config:
    templates:
      - name: government
        triggers:
          - "@gov"
        folder: Reference/Government
"""

from ..builtin import BUILTIN_FILTERS, SCORE_REGEX_MATCH, BuiltinFilter, MatchResult

# Lower threshold for gov - trust domains and .gov/.mil TLD
GOV_MATCH_THRESHOLD = 50


class GovFilter(BuiltinFilter):
    """Filter for government and official URLs."""

    def __init__(self) -> None:
        super().__init__("gov")

    def _check_special_patterns(self, url: str) -> int:
        """Check for .gov or .mil TLD patterns."""
        # Check .gov TLD
        gov_regex = self.data.regexes.get("gov_tld")
        if gov_regex and gov_regex.search(url):
            return SCORE_REGEX_MATCH

        # Check .mil TLD
        mil_regex = self.data.regexes.get("mil_tld")
        if mil_regex and mil_regex.search(url):
            return SCORE_REGEX_MATCH

        return 0

    def match(self, url: str) -> MatchResult:
        """Override to use lower threshold for gov sources."""
        result = super().match(url)
        is_match = result.score >= GOV_MATCH_THRESHOLD
        return MatchResult(is_match, result.score, result.reason)


# Register the filter
BUILTIN_FILTERS["gov"] = GovFilter()
