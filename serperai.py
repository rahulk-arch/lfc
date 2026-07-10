"""
serperai.py — Queue-based parallel Serper search worker
Each query is processed the moment it arrives. No batch waiting.
"""

import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import streamlit as st
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except (ImportError, KeyError, FileNotFoundError, RuntimeError):
    SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

SERPER_URL    = "https://google.serper.dev/search"
SERPER_WORKERS = 15

DOMAIN_RULES = {
    "wordpress.com": "Skip", "wikipedia.org": "Skip",
    "facebook.com": "Skip", "instagram.com": "Skip",
    "linkedin.com": "Skip", "youtube.com": "Skip",
    "twitter.com": "Skip", "x.com": "Skip",
    "reddit.com": "Skip", "quora.com": "Skip",
    "medium.com": "Skip", "scribd.com": "Skip",
    "drive.google.com": "Skip", "docs.google.com": "Skip",
    "dropbox.com": "Skip", "archive.org": "Skip",
    "researchgate.net": "Skip", "springer.com": "Skip",
    "pdfcoffee.com": "Skip", "academia.edu": "Skip",
    "static.pib.gov.in": "Skip",
    "give.do": "Directory", "csrbox.org": "Directory",
    "ngodarpan.gov.in": "Directory", "ngosindia.com": "Directory",
    "guidestarindia.org": "Directory", "ngofeed.com": "Directory",
    "fundsforngos.org": "Directory", "devex.com": "Directory",
    "timesofindia.indiatimes.com": "News", "hindustantimes.com": "News",
    "indianexpress.com": "News", "thehindu.com": "News",
    "ndtv.com": "News", "indiatoday.in": "News",
    "business-standard.com": "News", "scroll.in": "News",
    "thewire.in": "News",
}

DOCUMENT_KEYWORDS = [".pdf", "/pdf", "/doc", "/docs", "/download", "/document", "/media", "/files"]

JUNK_TITLE_KEYWORDS = [
    "top 10", "top 20", "top 50", "top 100", "best ngos", "list of",
    "scholarships", "how to apply", "upsc", "ias notes", "exam preparation",
    "job alert", "access denied", "403", "404", "just a moment",
]

def _is_junk(title):
    t = title.lower()
    return any(k in t for k in JUNK_TITLE_KEYWORDS)


def search_and_enqueue(query, category, location, url_queue, seen_urls, seen_urls_lock):
    """
    Searches one query via Serper and immediately puts results into url_queue.
    Called by the orchestrator's thread pool — fires as soon as a query is ready.
    """
    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 15},
            timeout=10
        )
        results = resp.json().get("organic", [])
    except Exception as e:
        print(f"  [Serper] Failed: {query[:50]} — {e}")
        return

    for r in results:
        title   = r.get("title", "").strip()
        url     = r.get("link",  "").strip()
        snippet = r.get("snippet", "").strip()

        if not url:
            continue
        url_lower = url.lower()
        if url_lower.endswith(".pdf"):
            continue
        if any(k in url_lower for k in DOCUMENT_KEYWORDS):
            continue
        if _is_junk(title):
            continue

        result_type = None
        for domain, rule in DOMAIN_RULES.items():
            if domain in url_lower:
                result_type = rule
                break

        if result_type == "Skip":
            continue
        if result_type is None and (".gov.in" in url_lower or ".gov" in url_lower):
            result_type = "Government"
        if result_type in ("Directory", "News"):
            continue
        if result_type is None:
            result_type = "Official Website"

        loc_score = f"{title} {snippet}".lower().count(location.lower())

        with seen_urls_lock:
            if url_lower in seen_urls:
                continue
            seen_urls.add(url_lower)

        url_queue.put({
            "Category": category,
            "Location": location,
            "Search Query": query,
            "Title": title,
            "URL": url,
            "Snippet": snippet,
            "Location Hint Score": loc_score,
            "Result Type": result_type,
        })
        print(f"  [Serper] Queued: {title[:55]}")