"""Optional Tavily and SEC EDGAR operations, preserving upstream metadata."""
from __future__ import annotations

import httpx

from finance_rag.config import WebSettings


class ExternalSources:
    def __init__(self, settings: WebSettings) -> None:
        self.settings = settings

    def tavily(self, query: str) -> list[dict]:
        if not self.settings.enabled:
            raise RuntimeError("Tavily is disabled by configuration")
        if not self.settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required")
        with httpx.Client(timeout=self.settings.timeout_seconds) as client:
            response = client.post("https://api.tavily.com/search", json={
                "api_key": self.settings.tavily_api_key, "query": query,
                "search_depth": "basic", "include_answer": False})
            response.raise_for_status()
            data = response.json()
        return [{"url": item["url"], "title": item.get("title", ""),
                 "content": item.get("content", ""), "score": item.get("score")}
                for item in data.get("results", [])]

    def fetch_web_result(self, url: str) -> dict:
        if not self.settings.enabled:
            raise RuntimeError("External web access is disabled by configuration")
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("Only HTTPS sources are supported")
        with httpx.Client(timeout=self.settings.timeout_seconds, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else str(response.url)
        for item in soup(["script", "style", "nav", "footer"]):
            item.decompose()
        return {"url": str(response.url), "title": title,
                "content": soup.get_text(" ", strip=True)}

    def _sec_get(self, url: str) -> dict:
        if not self.settings.enabled:
            raise RuntimeError("External sources are disabled by configuration")
        if not self.settings.sec_user_agent:
            raise ValueError("SEC_USER_AGENT is required for SEC requests")
        with httpx.Client(timeout=self.settings.timeout_seconds,
                          headers={"User-Agent": self.settings.sec_user_agent,
                                   "Accept": "application/json"}) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def search_edgar(self, company: str) -> list[dict]:
        tickers = self._sec_get("https://www.sec.gov/files/company_tickers.json")
        query = company.lower()
        return [{"name": row["title"], "ticker": row["ticker"],
                 "cik": str(row["cik_str"]).zfill(10),
                 "source_url": "https://www.sec.gov/files/company_tickers.json"}
                for row in tickers.values() if query in row["title"].lower()
                or query == row["ticker"].lower()]

    def get_sec_company_facts(self, cik: str) -> dict:
        if not cik.isdigit() or len(cik) > 10:
            raise ValueError("CIK must be numeric")
        padded = cik.zfill(10)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded}.json"
        data = self._sec_get(url)
        return {"source_url": url, "cik": data.get("cik"),
                "entityName": data.get("entityName"), "facts": data.get("facts", {})}

