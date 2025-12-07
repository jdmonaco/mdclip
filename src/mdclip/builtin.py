"""Built-in domain filter infrastructure for mdclip.

This module provides the base class and registry for built-in URL filters
that can be referenced in template triggers using @name syntax.

To add a new filter:
1. Create data/filtername/ with domains.yml and paths.yml
2. Create a subclass of BuiltinFilter
3. Register it in BUILTIN_FILTERS dict
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlparse

import yaml


BUILTIN_TRIGGER_PREFIX = "@"
MATCH_THRESHOLD = 70

# Score weights (shared across all filters)
SCORE_COMBINED_HIGH = 100
SCORE_DOMAIN_AND_PATH = 90
SCORE_REGEX_MATCH = 80
SCORE_DOMAIN = 50
SCORE_PATH = 40
SCORE_QUERY_PARAM = 30


class MatchResult(NamedTuple):
    """Result of URL matching."""

    is_match: bool
    score: int
    reason: str


@dataclass
class FilterData:
    """Loaded and cached filter data."""

    domains: set[str] = field(default_factory=set)
    path_patterns: list[str] = field(default_factory=list)
    query_params: list[str] = field(default_factory=list)
    regexes: dict[str, re.Pattern[str]] = field(default_factory=dict)
    combined_patterns: list[tuple[re.Pattern[str], str]] = field(default_factory=list)


class BuiltinFilter(ABC):
    """Base class for built-in URL filters."""

    def __init__(self, name: str):
        self.name = name

    @property
    def trigger(self) -> str:
        """The trigger string for this filter (e.g., '@academic')."""
        return f"{BUILTIN_TRIGGER_PREFIX}{self.name}"

    def _get_data_dir(self) -> Path:
        """Return path to this filter's data directory."""
        return Path(__file__).parent / "data" / self.name

    @cached_property
    def data(self) -> FilterData:
        """Load and cache filter data from YAML files."""
        data_dir = self._get_data_dir()
        result = FilterData()

        # Load domains
        domains_path = data_dir / "domains.yml"
        if domains_path.exists():
            with open(domains_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            # Accept any top-level list key
            for key, values in raw.items():
                if isinstance(values, list):
                    result.domains.update(d.lower() for d in values)

        # Load paths
        paths_path = data_dir / "paths.yml"
        if paths_path.exists():
            with open(paths_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            result.path_patterns = [p.lower() for p in raw.get("url_path_patterns", [])]
            result.query_params = raw.get("query_parameters", [])

            # Compile regex patterns
            for name, pattern in raw.get("regex_patterns", {}).items():
                try:
                    result.regexes[name] = re.compile(pattern, re.IGNORECASE)
                except re.error:
                    pass

            # Compile combined patterns
            for item in raw.get("combined_patterns", []):
                try:
                    compiled = re.compile(item["pattern"], re.IGNORECASE)
                    result.combined_patterns.append(
                        (compiled, item.get("confidence", "medium"))
                    )
                except re.error:
                    pass

        return result

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL, stripping www. prefix."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain[4:] if domain.startswith("www.") else domain

    def _check_domain(self, url: str) -> bool:
        """Check if URL matches a known domain."""
        url_domain = self._extract_domain(url)
        for known in self.data.domains:
            if url_domain == known or url_domain.endswith("." + known):
                return True
        return False

    def _check_path(self, url: str) -> bool:
        """Check if URL path contains known patterns."""
        path = urlparse(url).path.lower()
        return any(p in path for p in self.data.path_patterns)

    def _check_query_params(self, url: str) -> bool:
        """Check if URL query contains known parameters."""
        query = urlparse(url).query.lower()
        return any(p.rstrip("=") + "=" in query for p in self.data.query_params)

    def _check_combined_patterns(self, url: str) -> tuple[bool, str]:
        """Check URL against combined patterns."""
        for pattern, confidence in self.data.combined_patterns:
            if pattern.search(url):
                return True, confidence
        return False, ""

    @abstractmethod
    def _check_special_patterns(self, url: str) -> int:
        """Check filter-specific patterns. Return score contribution."""
        pass

    def match(self, url: str) -> MatchResult:
        """Determine if URL matches this filter using scoring."""
        score = 0
        reasons: list[str] = []

        # High-confidence combined patterns (fast path)
        combined_match, confidence = self._check_combined_patterns(url)
        if combined_match and confidence == "high":
            return MatchResult(True, SCORE_COMBINED_HIGH, "high-confidence pattern")

        # Filter-specific patterns (e.g., DOI for academic)
        special_score = self._check_special_patterns(url)
        if special_score > 0:
            score += special_score
            reasons.append("special pattern")

        # Domain + path combination
        domain_match = self._check_domain(url)
        path_match = self._check_path(url)

        if domain_match and path_match:
            score = max(score, SCORE_DOMAIN_AND_PATH)
            reasons.extend(["domain", "path"])
        elif domain_match:
            score = max(score, SCORE_DOMAIN)
            reasons.append("domain")
        elif path_match:
            score = max(score, SCORE_PATH)
            reasons.append("path")

        # Query param bonus
        if self._check_query_params(url):
            score += SCORE_QUERY_PARAM
            reasons.append("query param")

        is_match = score >= MATCH_THRESHOLD
        return MatchResult(
            is_match, score, ", ".join(reasons) if reasons else "no signals"
        )

    def matches(self, url: str) -> bool:
        """Check if URL matches this filter."""
        return self.match(url).is_match


# Registry of built-in filters (populated by submodules)
BUILTIN_FILTERS: dict[str, BuiltinFilter] = {}


def is_builtin_trigger(pattern: str) -> bool:
    """Check if pattern is a built-in trigger (@name)."""
    pattern = pattern.strip().lower()
    return pattern.startswith(BUILTIN_TRIGGER_PREFIX) and pattern[1:] in BUILTIN_FILTERS


def get_builtin_filter(pattern: str) -> BuiltinFilter | None:
    """Get the filter for a built-in trigger, or None."""
    pattern = pattern.strip().lower()
    if pattern.startswith(BUILTIN_TRIGGER_PREFIX):
        return BUILTIN_FILTERS.get(pattern[1:])
    return None


def matches_builtin(url: str, pattern: str) -> bool:
    """Check if URL matches a built-in filter trigger."""
    filt = get_builtin_filter(pattern)
    return filt.matches(url) if filt else False
