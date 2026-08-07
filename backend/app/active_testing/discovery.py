"""
active_testing/discovery.py

A DELIBERATELY MINIMAL discovery step. Data Flow 3 in the project spec
assumes "discovered forms/params from the recon phase" as an input, but
the recon module built in Task 3 (nmap-based) only does host/port/banner
discovery -- it doesn't parse HTML. Something has to turn "port 443 is
open and looks like HTTP" into "here are the actual forms/params to test."

SCOPE LIMITS (flag for your limitations section):
  - Single page only (the target's root URL / each discovered HTTP(S)
    port's root). No crawling of linked pages, no sitemap parsing, no
    following redirects to discover additional pages.
  - Static HTML parsing only. Forms/inputs rendered client-side by JS
    frameworks (React/Vue SPAs building forms at runtime) will NOT be
    discovered -- this only sees what's in the initial HTML response.
  - No authentication -- can't discover forms that live behind a login.
A real implementation would use a headless browser (Playwright) to
render the page fully and would crawl multiple pages/depth. That's a
substantially larger scope (and a much larger active-testing surface,
which cuts against "controlled" and "rate-limited") -- explicitly left
as future work rather than built here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, parse_qs

import httpx

logger = logging.getLogger("vulnara.active_testing.discovery")


@dataclass
class TestTarget:
    """One injectable point: a form field, or a URL query parameter."""
    url: str
    method: str  # "GET" | "POST"
    param_name: str
    source: str  # "form" | "query_param"
    other_params: dict[str, str] = field(default_factory=dict)
    # other_params: the rest of the form's fields/query params, held at
    # their default/original values while we vary param_name -- keeps the
    # request realistic instead of submitting a form with only one field
    # populated, which some apps would reject outright regardless of payload.


class _FormParser(HTMLParser):
    """Minimal HTML form parser -- stdlib only, no BeautifulSoup dependency."""

    def __init__(self, page_url: str):
        super().__init__()
        self.page_url = page_url
        self.forms: list[TestTarget] = []
        self._current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)

        if tag == "form":
            action = attrs_dict.get("action", "")
            method = (attrs_dict.get("method") or "GET").upper()
            self._current_form = {
                "url": urljoin(self.page_url, action) if action else self.page_url,
                "method": method,
                "fields": {},
            }

        elif tag in ("input", "textarea") and self._current_form is not None:
            name = attrs_dict.get("name")
            if name:
                self._current_form["fields"][name] = attrs_dict.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            fields = self._current_form["fields"]
            for field_name in fields:
                # One TestTarget per field: we vary one field at a time,
                # holding the others at their default values (see other_params).
                self.forms.append(
                    TestTarget(
                        url=self._current_form["url"],
                        method=self._current_form["method"],
                        param_name=field_name,
                        source="form",
                        other_params={k: v for k, v in fields.items() if k != field_name},
                    )
                )
            self._current_form = None


def _extract_query_params(page_url: str) -> list[TestTarget]:
    """If the seed URL itself has query params, treat each as a test target."""
    parsed = urlparse(page_url)
    if not parsed.query:
        return []

    params = parse_qs(parsed.query)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    targets = []
    for name in params:
        others = {k: v[0] for k, v in params.items() if k != name}
        targets.append(
            TestTarget(url=base_url, method="GET", param_name=name, source="query_param", other_params=others)
        )
    return targets


async def discover_targets(base_url: str, timeout_seconds: float = 10.0) -> list[TestTarget]:
    """
    Fetches one page and extracts form fields + query params as test
    targets. Returns an empty list (not an exception) if the page can't
    be fetched or has no forms -- "nothing to actively test" is a valid,
    common outcome, not a failure.
    """
    targets: list[TestTarget] = []
    targets.extend(_extract_query_params(base_url))

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            resp = await client.get(base_url)
            resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Discovery could not fetch %s: %s", base_url, e)
        return targets

    parser = _FormParser(page_url=str(resp.url))
    parser.feed(resp.text)
    targets.extend(parser.forms)

    return targets
