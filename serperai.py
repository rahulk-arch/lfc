import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

SERPER_API_KEY = "a5acda6d15aec43fbf98d197a024e42891bf84cd"

'''
try:
    import streamlit as st
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except (ImportError, KeyError, FileNotFoundError):
    SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
'''
SERPER_URL = "https://google.serper.dev/search"
SEARCH_WORKERS = 15  # safe now — Serper is a real rate-limited API, not a scraper


def search_web(queries, category, location):

    DOMAIN_RULES = {
        # ---------- Skip ----------
        "wordpress.com": "Skip",
        "pdfcoffee.com": "Skip",
        "rocketguestposting.com": "Skip",
        "secretattractions.com": "Skip",
        "link.springer.com": "Skip",
        "springer.com": "Skip",
        "researchgate.net": "Skip",   
        "companydatabase.in": "Skip",
        "wikipedia.org": "Skip",
        "facebook.com": "Skip",
        "instagram.com": "Skip",
        "linkedin.com": "Skip",
        "youtube.com": "Skip",
        "twitter.com": "Skip",
        "x.com": "Skip",
        "reddit.com": "Skip",
        "quora.com": "Skip",
        "medium.com": "Skip",
        "pinterest.com": "Skip",
        "scribd.com": "Skip",
        "issuu.com": "Skip",
        "academia.edu": "Skip",
        "researchgate.net": "Skip",
        "drive.google.com": "Skip",
        "docs.google.com": "Skip",
        "dropbox.com": "Skip",
        "static.pib.gov.in": "Skip",
        "archive.org": "Skip",
 
        # ---------- Directory ----------
        "give.do": "Directory",
        "csrbox.org": "Directory",
        "fundsforngos.org": "Directory",
        "guidestarindia.org": "Directory",
        "ngofeed.com": "Directory",
        "ngodarpan.gov.in": "Directory",
        "ngobase.org": "Directory",
        "ngosindia.com": "Directory",
            "devex.com": "Directory",
 
        # ---------- News ----------
        "timesofindia.indiatimes.com": "News",
        "hindustantimes.com": "News",
        "indianexpress.com": "News",
        "thehindu.com": "News",
        "ndtv.com": "News",
        "livemint.com": "News",
        "firstpost.com": "News",
        "thestatesman.com": "News",
        "ythisnews.com": "News",
        "legendofficers.com": "News",
        "news18.com": "News",
        "indiatoday.in": "News",
        "business-standard.com": "News",
        "aninews.in": "News",
        "theprint.in": "News",
        "scroll.in": "News",
        "thewire.in": "News",
        "thelogicalindian.com": "News",
 
        # ---------- Other ----------
        "shiksha.com": "Other",
        "careerindia.com": "Other",
        "jagranjosh.com": "Other",
        "byjus.com": "Other",
        "testbook.com": "Other",
 
        # ---------- Blog / Scholarship / List sites ----------
        "advance-africa.com": "Skip",
        "youthkiawaaz.com": "Skip",
        "ipleaders.in": "Skip",
        "cleartax.in": "Skip",
        "mca.gov.in": "Skip", 
        "opportunitydesk.org": "Skip",
        "scholars4dev.com": "Skip",
        "afterschoolafrica.com": "Skip",
        "indiacsr.in": "Skip",
        "impriindia.com": "Skip",
        "civilsdaily.com": "Skip",
        "vajiramandravi.com": "Skip",
        "pwonlyias.com": "Skip",
        "educationforallinindia.com": "Skip",
        "teachers.institute": "Skip",
        "narayanseva.org": "Skip",
        "legalonus.com": "Skip",
        "writinglaw.com": "Skip",
        "pathlegal.in": "Skip",
        "scarymommy.com": "Skip",
        "influvera.com": "Skip",
        "socialnative.com": "Skip",
        "positive-parenting-ally.com": "Skip",
        "dialogue.earth": "Skip",
        "wired.com": "Skip",
        "fortune.com": "Skip",
        "rt.com": "Skip",
        "bbc.com": "Skip",
        "bbc.co.uk": "Skip",
        "forbes.com": "Skip",
        "reuters.com": "Skip",
        "apnews.com": "Skip",
        "theguardian.com": "Skip",
        "jobalertshub.com": "Skip",
        "indianbureaucracy.com": "Skip",
        "morungexpress.com": "Skip",
    }
 

    DIRECTORY_KEYWORDS = [
        "top","best","directory","directories","list",
        "member","members","partners","partner ngos",
        "working with","organizations working",
        "ngo list","charity list","foundation list",
        "registered ngos","nonprofit","database",
        "resources","resource",
        "top 10","top 20","top 50","top 100"
    ]

    DOCUMENT_KEYWORDS = [
        ".pdf", "/pdf",
        "/doc", "/docs",
        "/download", "/downloads",
        "/upload", "/uploads",
        "/document", "/documents",
        "/media", "/files"
    ]

    JUNK_TITLE_KEYWORDS = [
        "top 10", "top 20", "top 50", "top 100", "best ngos", "list of",
        "scholarships", "scholarship", "how to apply", "funding opportunities",
        "inspiring stories", "making a difference", "upsc", "ias notes",
        "study material", "exam preparation", "recruitment", "job alert",
        "press release", "press information bureau", "pib.gov.in",
        "just a moment", "access denied", "403", "404",
    ]

    def is_junk_title(title: str) -> bool:
        t = title.lower()
        return any(k in t for k in JUNK_TITLE_KEYWORDS)

    existing_urls = set()
    search_results = []

    def process_query(i, query, total):
        print(f"[{i}/{total}] Searching: {query}")

        print("API KEY:", repr(SERPER_API_KEY))
        print("API KEY LENGTH:", len(SERPER_API_KEY) if SERPER_API_KEY else 0)

        try:
            response = requests.post(
                SERPER_URL,
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": 15},
                timeout=10
            )

            data = response.json()
            print(data)
            results = data.get("organic", [])
            print("organic results:", len(results))

        except Exception as e:
            print(f"Failed: {query} — {e}")
            return []

        matches = []
        for result in results:
            title = result.get("title", "").strip()
            url = result.get("link", "").strip()
            snippet = result.get("snippet", "").strip()

            if not url:
                continue

            title_lower = title.lower()
            url_lower = url.lower()

            if url_lower.endswith(".pdf"):
                continue
            if any(k in url_lower for k in DOCUMENT_KEYWORDS):
                continue
            if is_junk_title(title):
                print(f"  [JUNK TITLE] Skipping: {title}")
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
            if result_type is None and any(k in title_lower for k in DIRECTORY_KEYWORDS):
                result_type = "Directory"
            if result_type is None and any(k in url_lower for k in DIRECTORY_KEYWORDS):
                result_type = "Directory"
            if result_type is None:
                result_type = "Official Website"

            location_lower = location.lower()
            combined_text = f"{title} {snippet}".lower()
            location_hint_score = combined_text.count(location_lower)

            matches.append({
                "Category": category,
                "Location": location,
                "Search Query": query,
                "Title": title,
                "URL": url,
                "Snippet": snippet,
                "Location Hint Score": location_hint_score,
                "Result Type": result_type,
            })

        return matches

    total = len(queries)

    with ThreadPoolExecutor(max_workers=SEARCH_WORKERS) as executor:
        futures = {
            executor.submit(process_query, i, q, total): i
            for i, q in enumerate(queries, start=1)
        }
        for future in as_completed(futures):
            for row in future.result():
                if row["URL"].lower() not in existing_urls:
                    existing_urls.add(row["URL"].lower())
                    search_results.append(row)

    print("Done!")
    return search_results
