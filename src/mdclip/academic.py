"""Academic/journal URL filter for mdclip.

This filter detects academic and scientific journal article URLs using
a combination of known publisher domains and URL path patterns.

Usage in config:
    templates:
      - name: papers
        triggers:
          - "@academic"
        folder: Reference/Papers
"""

from .builtin import BUILTIN_FILTERS, SCORE_REGEX_MATCH, BuiltinFilter


class AcademicFilter(BuiltinFilter):
    """Filter for academic and scientific journal URLs."""

    def __init__(self) -> None:
        super().__init__("academic")

    def _check_special_patterns(self, url: str) -> int:
        """Check for DOI patterns in the URL."""
        doi_regex = self.data.regexes.get("doi_pattern")
        if doi_regex and doi_regex.search(url):
            return SCORE_REGEX_MATCH
        return 0


# Register the filter
BUILTIN_FILTERS["academic"] = AcademicFilter()
