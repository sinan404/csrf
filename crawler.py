#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Crawler
-----------
Crawls a web application and discovers pages and forms.

Usage:
    python crawler.py <url> [--depth N] [--delay S]

Examples:
    python crawler.py https://example.com
    python crawler.py https://example.com --depth 3
"""

import sys
import argparse
import time
import urllib.parse
from collections import deque
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Install with: pip install requests beautifulsoup4 colorama")
    sys.exit(1)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def same_origin(url1: str, url2: str) -> bool:
    return urllib.parse.urlparse(url1).netloc == urllib.parse.urlparse(url2).netloc


# ─── Core crawler ───────────────────────────────────────────────────────────

class Crawler:
    def __init__(self, start_url: str, max_depth: int = 2, delay: float = 0.3):
        self.start_url = normalize_url(start_url)
        self.max_depth = max_depth
        self.delay = delay

        self.visited: set[str] = set()
        self.pages: list[dict] = []
        self.pages_scanned = 0
        self.forms_found = 0

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WebCrawler/1.0",
            "Accept": "text/html,application/xhtml+xml",
        })

    def fetch(self, url: str):
        try:
            return self.session.get(url, timeout=10, allow_redirects=True)
        except Exception as e:
            print(f"  {Fore.RED}[ERR] {url}: {e}{Style.RESET_ALL}")
            return None

    def extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        links = []
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full = urllib.parse.urljoin(base_url, href).split("#")[0].split("?")[0]
            if same_origin(self.start_url, full) and full not in self.visited:
                links.append(full)
        return links

    def collect_form_info(self, form, page_url: str):
        """Collect basic metadata about a form (no security analysis)."""
        method = (form.get("method") or "GET").upper()
        action = form.get("action") or page_url
        action_url = urllib.parse.urljoin(page_url, action)
        self.forms_found += 1

        inputs = form.find_all(["input", "select", "textarea", "button"])
        field_names = [
            (i.get("name") or "").strip()
            for i in inputs if i.get("name")
        ]

        return {
            "action": action_url,
            "method": method,
            "fields": field_names,
        }

    def crawl(self):
        print(f"\n{Fore.CYAN}-- Web Crawler --{Style.RESET_ALL}")
        print(f"  Target : {self.start_url}")
        print(f"  Depth  : {self.max_depth}")
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        queue = deque([(self.start_url, 0)])

        while queue:
            url, depth = queue.popleft()
            if url in self.visited:
                continue
            self.visited.add(url)

            print(f"  {Fore.WHITE}[{depth}/{self.max_depth}] {url}{Style.RESET_ALL}")
            resp = self.fetch(url)
            if resp is None:
                continue

            self.pages_scanned += 1

            try:
                soup = BeautifulSoup(resp.text, "html.parser")
            except Exception:
                continue

            # Collect form metadata
            page_forms = []
            for form in soup.find_all("form"):
                page_forms.append(self.collect_form_info(form, url))

            self.pages.append({
                "url": url,
                "depth": depth,
                "status": resp.status_code,
                "forms": page_forms,
            })

            # Enqueue child links
            if depth < self.max_depth:
                for link in self.extract_links(soup, url):
                    if link not in self.visited:
                        queue.append((link, depth + 1))

            time.sleep(self.delay)

        self._print_report()

    def _print_report(self):
        print(f"\n{'=' * 55}")
        print(f"  {Fore.CYAN}CRAWL RESULTS{Style.RESET_ALL}")
        print(f"{'=' * 55}")
        print(f"  Pages scanned : {self.pages_scanned}")
        print(f"  Forms found   : {self.forms_found}")
        print(f"{'=' * 55}\n")

        if self.pages:
            print(f"{Fore.CYAN}-- Discovered Pages --{Style.RESET_ALL}\n")
            for p in self.pages:
                status_color = Fore.GREEN if p["status"] == 200 else Fore.YELLOW
                print(f"  {status_color}[{p['status']}]{Style.RESET_ALL} {p['url']}")

                if p["forms"]:
                    for f in p["forms"]:
                        print(f"       {Fore.WHITE}Form: {f['method']} -> {f['action']}{Style.RESET_ALL}")
                        if f["fields"]:
                            print(f"         Fields: {f['fields']}")
            print()
        else:
            print(f"  {Fore.YELLOW}No pages were reachable.{Style.RESET_ALL}\n")

        print(f"  Done: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def get_results(self) -> dict:
        """Return crawl results as a dictionary for programmatic use."""
        return {
            "start_url": self.start_url,
            "pages_scanned": self.pages_scanned,
            "forms_found": self.forms_found,
            "pages": self.pages,
        }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Web Crawler — discover pages and forms")
    parser.add_argument("url", help="Target URL to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth (default: 2)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between requests (default: 0.3s)")
    args = parser.parse_args()

    crawler = Crawler(args.url, max_depth=args.depth, delay=args.delay)
    crawler.crawl()


if __name__ == "__main__":
    main()