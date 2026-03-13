"""Cookie loading and parsing for authenticated requests."""

from pathlib import Path
from urllib.parse import urlparse
from typing import Optional


def load_cookies_from_file(path: Path) -> list[dict]:
    """Parse Netscape cookies.txt format.

    Format: domain, include_subdomains, path, secure, expires, name, value
    Lines starting with # are comments. Fields are tab-separated.

    Returns list of cookie dicts with: domain, path, secure, expires, name, value
    """
    cookies = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies.append({
                    "domain": parts[0],
                    "path": parts[2],
                    "secure": parts[3].upper() == "TRUE",
                    "expires": int(parts[4]) if parts[4].isdigit() else 0,
                    "name": parts[5],
                    "value": parts[6],
                })
    return cookies


def filter_cookies_for_url(cookies: list[dict], url: str) -> list[dict]:
    """Filter cookies applicable to the given URL.

    Matches cookies by domain (including subdomain matching) and path prefix.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path or "/"

    result = []
    for c in cookies:
        cookie_domain = c["domain"].lower().lstrip(".")
        # Match exact domain or subdomain
        if domain == cookie_domain or domain.endswith("." + cookie_domain):
            # Match path prefix
            if path.startswith(c["path"]):
                result.append(c)
    return result


def format_cookie_header(cookies: list[dict]) -> str:
    """Format cookies as HTTP Cookie header value."""
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)


def _get_candidate_domains(url: str) -> list[str]:
    """Get candidate domain names for cookie file matching.

    Returns [full_hostname, base_domain] — e.g., ["www.wired.com", "wired.com"].
    If no subdomain prefix, returns single-element list.
    """
    netloc = urlparse(url).netloc.lower()
    # Strip port if present
    if ":" in netloc:
        netloc = netloc.rsplit(":", 1)[0]

    candidates = [netloc]
    # Add base domain if there's a subdomain
    parts = netloc.split(".")
    if len(parts) > 2:
        base = ".".join(parts[-2:])
        if base != netloc:
            candidates.append(base)
    return candidates


def find_cookies_for_url(url: str, search_dirs: list[Path]) -> Optional[Path]:
    """Find a cookie file matching the given URL's domain.

    Search priority (first match wins, newest by mtime within each tier):
    1. Domain-prefixed files: {domain}_cookies.txt
    2. Generic cookies.txt
    3. Broad glob fallback: *{base_domain}*cookies*.txt
    """
    candidates = _get_candidate_domains(url)
    base_domain = candidates[-1]  # last is always the shortest

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue

        try:
            files = list(search_dir.iterdir())
        except OSError:
            continue

        # Tier 1: Domain-prefixed files
        tier1: list[Path] = []
        for domain in candidates:
            pattern = f"{domain}_cookies.txt"
            for f in files:
                if f.name == pattern and f.is_file():
                    tier1.append(f)
        if tier1:
            return max(tier1, key=lambda p: p.stat().st_mtime)

        # Tier 2: Generic cookies.txt
        for f in files:
            if f.name == "cookies.txt" and f.is_file():
                return f

        # Tier 3: Broad glob fallback
        tier3: list[Path] = []
        for f in files:
            name = f.name.lower()
            if (
                base_domain in name
                and "cookies" in name
                and name.endswith(".txt")
                and f.is_file()
            ):
                tier3.append(f)
        if tier3:
            return max(tier3, key=lambda p: p.stat().st_mtime)

    return None
