import time
from ddgs import DDGS
 

def search_web(queries, category, location):   
    SEARCH_WORKERS = 3

    # Domain Rules
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

    total = len(queries)

    for i, query in enumerate(queries, start=1):

        print(f"[{i}/{total}] Searching: {query}")
    
        results = []
 
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=15, search_workers=SEARCH_WORKERS))

                time.sleep(1)
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(5)
                else:
                    print(f"Failed: {query}")
                    print(e)
 
        if not results:
            continue
            
        for rank, result in enumerate(results, start=1):
 
            title = result.get("title", "").strip()
            url = result.get("href", "").strip()

            if not url:
                continue
 
            title_lower = title.lower()
            url_lower = url.lower()
 
            if url_lower in existing_urls:
                continue
 
            if url_lower.endswith(".pdf"):
                continue
 
            if any(k in url_lower for k in DOCUMENT_KEYWORDS):
                continue
 
            # Filter junk titles before any further processing
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
 
            search_results.append({
                "Category": category,
                "Location": location,
                "Search Query": query,
                "Title": title,
                "URL": url,
                "Result Type": result_type,
            })
 
            existing_urls.add(url_lower)
 
    print("Done!")
    return search_results
 