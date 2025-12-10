"""Cookie loading and parsing for authenticated requests."""

from pathlib import Path
from urllib.parse import urlparse


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
