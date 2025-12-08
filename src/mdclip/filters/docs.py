"""Software documentation URL filter for mdclip.

This filter detects documentation URLs for software, APIs, and
technical specifications. Requires domain + path signals for precision.

Usage in config:
    templates:
      - name: documentation
        triggers:
          - "@docs"
        folder: Reference/Docs
"""

from ..builtin import BUILTIN_FILTERS, BuiltinFilter


class DocsFilter(BuiltinFilter):
    """Filter for software documentation URLs."""

    def __init__(self) -> None:
        super().__init__("docs")

    def _check_special_patterns(self, url: str) -> int:
        """No special patterns for docs filter."""
        return 0


# Register the filter (uses default MATCH_THRESHOLD = 70)
BUILTIN_FILTERS["docs"] = DocsFilter()
