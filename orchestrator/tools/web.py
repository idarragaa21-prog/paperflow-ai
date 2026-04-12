from __future__ import annotations

from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import json
import re

DEFAULT_HEADERS = {
    'User-Agent': 'OpenClaw-Orchestrator/1.0 (+local development)',
    'Accept': 'application/json,application/pdf,text/html;q=0.9,*/*;q=0.8',
}
BROWSER_PATH = '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser'


def fetch_bytes(url: str, *, timeout: int = 20) -> tuple[bytes, dict[str, str], str]:
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=timeout) as response:
        body = response.read()
        headers = {k.lower(): v for k, v in response.headers.items()}
        return body, headers, response.geturl()


def fetch_json(url: str, *, timeout: int = 20) -> dict:
    body, _, _ = fetch_bytes(url, timeout=timeout)
    return json.loads(body.decode('utf-8'))


def safe_fetch_json(url: str, *, timeout: int = 20) -> tuple[dict | None, str | None]:
    try:
        return fetch_json(url, timeout=timeout), None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, str(exc)


def safe_fetch_bytes(url: str, *, timeout: int = 20) -> tuple[tuple[bytes, dict[str, str], str] | None, str | None]:
    try:
        return fetch_bytes(url, timeout=timeout), None
    except (HTTPError, URLError, TimeoutError, IncompleteRead) as exc:
        return None, str(exc)


def find_pdf_links_in_html(html: str, base_url: str) -> list[str]:
    matches = set()
    for quote_char in ['"', "'"]:
        marker = f'href={quote_char}'
        start = 0
        while True:
            index = html.find(marker, start)
            if index == -1:
                break
            href_start = index + len(marker)
            href_end = html.find(quote_char, href_start)
            if href_end == -1:
                break
            href = html[href_start:href_end].strip()
            start = href_end + 1
            lowered = href.lower()
            if '.pdf' in lowered or 'pdf' in lowered:
                matches.add(urljoin(base_url, href))
    return sorted(matches)


def extract_html_summary(html: str, *, max_links: int = 12) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'lxml')
    title = (soup.title.string or '').strip() if soup.title and soup.title.string else None
    texts = []
    for node in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
        text = ' '.join(node.get_text(' ', strip=True).split())
        if text and len(text) > 30:
            texts.append(text)
        if len(' '.join(texts)) > 4000:
            break
    links: list[dict[str, str]] = []
    for anchor in soup.find_all('a', href=True):
        href = anchor.get('href', '').strip()
        text = ' '.join(anchor.get_text(' ', strip=True).split())
        if not href:
            continue
        links.append({'text': text[:120], 'href': href})
        if len(links) >= max_links:
            break
    return {
        'title': title,
        'text': '\n'.join(texts)[:4000],
        'links': links,
    }


def browser_navigate(url: str, *, timeout_ms: int = 15000) -> dict:
    final = {'requested_url': url, 'final_url': url, 'title': None, 'text': '', 'links': [], 'method': 'http'}
    page_html = None
    if Path(BROWSER_PATH).exists():
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path=BROWSER_PATH,
                    args=['--disable-gpu', '--no-first-run'],
                )
                page = browser.new_page()
                page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
                page.wait_for_timeout(1500)
                page_html = page.content()
                final['final_url'] = page.url
                final['title'] = page.title()
                browser.close()
                final['method'] = 'playwright'
        except Exception as exc:
            final['playwright_error'] = str(exc)

    if not page_html:
        fetched, error = safe_fetch_bytes(url, timeout=max(10, timeout_ms // 1000))
        if error:
            final['error'] = error
            return final
        body, _, final_url = fetched
        page_html = body.decode(errors='ignore')
        final['final_url'] = final_url

    summary = extract_html_summary(page_html)
    final['title'] = final['title'] or summary.get('title')
    final['text'] = summary.get('text', '')
    links = []
    for item in summary.get('links', []):
        href = item.get('href') or ''
        links.append({'text': item.get('text', ''), 'href': urljoin(final['final_url'], href)})
    final['links'] = links
    return final


def looks_like_url(value: str) -> bool:
    return bool(re.match(r'^https?://', value.strip(), flags=re.IGNORECASE))
