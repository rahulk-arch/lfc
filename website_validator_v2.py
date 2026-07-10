"""
website_validator_v2.py — Queue-based parallel validator
Pulls one URL at a time from url_queue, validates it immediately,
pushes Valid results into valid_queue. No batch waiting.
"""

import json
import threading
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── All your original signal lists — completely unchanged ───────────────────

INVALID_DOMAINS = {
    "vajiramandravi.com", "behtarlife.com", "advance-africa.com",
    "opportunitydesk.org", "scholars4dev.com", "afterschoolafrica.com",
    "influencers.feedspot.com", "influvera.com", "socialnative.com",
    "grynow.in", "indiacsr.in", "impriindia.com", "civilsdaily.com",
    "educationforallinindia.com", "teachers.institute", "narayanseva.org",
    "indianbureaucracy.com", "sitelike.org", "danamojo.org", "catalog.in",
    "legalonus.com", "writinglaw.com", "pathlegal.in", "gojuris.in",
    "dokumen.pub", "bing.com", "education21.in", "highereducationdigest.com",
    "globaleducationnews.org", "pdfcoffee.com", "epdf.pub", "epdf.tips",
    "slideshare.net", "scarymommy.com", "positive-parenting-ally.com",
    "theindianpublisher.com", "justbaazaar.com", "indiamart.com",
    "justdial.com", "sulekha.com", "tradeindia.com", "exportersindia.com",
    "dir.indiamart.com", "ok.ru", "lootbar.com",
}

INVALID_URL_PATTERNS = [
    "/directory/", "/directories/", "/listing/", "/list/", "/ngo-list/",
    "/ngos/", "/top-ngos/", "/best-ngos/", "/compare/", "/reviews/",
    "/article", "/articles", "/blog", "/blogs", "/news", "/post/",
    "/story/", "/insights/", "/press-release", "/press_release",
    "/profileshow/", "/gallery/",
    "/2020/", "/2021/", "/2022/", "/2023/", "/2024/", "/2025/",
    ".pdf", "/download", "/pages/", "/event/", "/category/", "/tag/",
    "/wp-content/", "/pub/", "/press/",
    "/top-100", "/top-50", "/top-10", "/best-of",
    "/list-of-ngos", "/list-of-nonprofits", "ngo-list", "nonprofit-list",
]

BLOCKED_SIGNALS = [
    "just a moment", "checking your browser", "attention required",
    "access denied", "enable javascript and cookies",
    "ddos protection", "ray id", "please wait while we verify",
]

ORG_NAV_KEYWORDS = [
    "about us", "about", "who we are", "our mission", "our vision",
    "contact us", "contact", "reach us", "get in touch",
    "our work", "what we do", "programs", "projects",
    "donate", "support us", "get involved", "volunteer",
    "annual report", "board of directors", "team", "leadership",
    "our impact", "careers", "publications",
]

ORG_SCHEMA_TYPES = [
    "Organization", "NGO", "GovernmentOrganization",
    "EducationalOrganization", "NonProfit",
]

JUNK_TITLE_SIGNALS = [
    "best ngos", "list of", "scholarships", "scholarship", "how to apply",
    "funding opportunities", "inspiring stories", "upsc", "ias notes",
    "study material", "exam preparation", "recruitment", "job alert",
    "just a moment", "access denied", "403 forbidden", "404",
    "press release", "news:", "| news", "latest news",
    "gta 6", "quotes in hindi", "influencers in 2026", "alternatives", "sites like",
]

NGO_KEYWORDS = [
    "foundation", "trust", "society", "ngo", "nonprofit", "non profit",
    "donate", "volunteer", "mission", "impact", "community", "education",
    "health", "livelihood", "children", "annual report", "financial",
    "csr", "governance", "transparency",
]

COLLABORATION_SIGNALS = [
    "donate", "donate now", "volunteer", "get involved", "our work",
    "our impact", "our mission", "our vision", "our programs", "our projects",
    "campaigns", "beneficiaries", "our causes", "support us", "partner with us",
    "who we are",
]

CHILD_PROGRAMS = [
    "our programs", "our programme", "our programmes", "our initiatives",
    "our projects", "learning centre", "learning center", "bridge school",
    "community school", "after school", "school readiness",
    "underprivileged children", "education for underprivileged",
    "street children", "slum children", "marginalized children",
    "out-of-school children", "education access", "school enrollment",
    "children", "child education", "child development", "child rights",
    "child protection", "child welfare", "child sponsorship", "sponsor a child",
    "early childhood", "balwadi", "anganwadi",
    "hostel", "residential home", "child care centre", "orphanage", "life skills",
]

CHILD_NGO_SIGNALS = [
    "child education", "child rights", "child protection", "child sponsorship",
    "children", "school children", "children we serve", "children enrolled",
    "children reached", "working with children", "slum children",
    "orphanage", "child care", "early childhood", "education for children",
    "child development",
]

EDUCATION_SIGNALS = [
    "school", "schools", "student", "students", "teacher", "teachers",
    "classroom", "primary school", "government school", "municipal school",
    "school children", "pre-school", "preschool", "kindergarten", "play school",
]

CHILD_SERVICE_SIGNALS = [
    "learning centre", "learning center", "education centre", "education center",
    "bridge school", "after school", "school readiness",
    "community school", "child care centre",
]

CHILD_NAV = [
    "child rights", "child protection", "child sponsorship", "early childhood",
    "bridge school", "after school", "school children", "community school",
    "government school", "municipal school", "anganwadi", "orphanage", "child care",
]

NGO_PAGES = [
    "about", "contact", "donate", "volunteer", "program", "programs",
    "project", "projects", "education program", "child sponsorship",
    "impact", "our-work", "what-we-do", "financial", "annual-report",
    "governance", "board", "team", "leadership", "partner", "partners",
]

FOOTER_KEYWORDS = [
    "annual report", "financial", "financials", "governance", "transparency",
    "80g", "12a", "fcra", "donate", "volunteer", "csr", "impact",
    "privacy policy", "terms of use", "contact", "about us",
]

PREMIUM_SCHOOL_KEYWORDS = [
    "international school", "ib curriculum", "cambridge curriculum",
    "igcse", "ibdp", "boarding school", "world school", "global school",
    "residential campus", "admission open", "admission enquiry",
    "fee structure", "tuition fee", "online admission",
]

BUSINESS_SIGNALS = [
    "mutual fund", "insurance", "loan", "banking", "stock market",
    "investor relations", "shareholders", "our products",
    "our services", "customer support",
]

SEO_SIGNALS = [
    "guest post", "guest posting", "write for us", "submit article",
    "submit guest post", "advertise with us", "sponsored post",
    "become a contributor", "accepting guest posts",
]

COMPANY_SIGNALS = [
    "investor relations", "shareholders", "corporate governance",
    "quarterly results", "our products", "our services", "business units",
]

BAD_TITLE = ["directory", "blog", "article", "list of", "top 10", "top 20", "top 50", "top 100"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 6
MAX_WORKERS     = 15


def _normalize_homepage(url):
    try:
        p = urlparse(url)
        scheme = p.scheme if p.scheme in ("http", "https") else "https"
        return f"{scheme}://{p.netloc}"
    except Exception:
        return url

def _is_blacklisted(url):
    try:
        netloc = urlparse(url).netloc.lower().lstrip("www.")
        return any(netloc == d or netloc.endswith("." + d) for d in INVALID_DOMAINS)
    except Exception:
        return False

def _has_invalid_pattern(url):
    return any(pat in url.lower() for pat in INVALID_URL_PATTERNS)

def _strip_www(netloc):
    return netloc.lower()[4:] if netloc.lower().startswith("www.") else netloc.lower()


def validate_one(item, category_signals, location, seen_domains, seen_domains_lock):
    """
    Validates a single search result item.
    Returns the item dict with Validation="Valid"/"Invalid"/"Unsure" added,
    or None if it should be skipped entirely.
    """
    url   = item["URL"]
    title = item["Title"]

    # ── Fast checks (no network) ───────────────────────────────────────────
    if _is_blacklisted(url):
        return None
    if _has_invalid_pattern(url):
        return None
    if any(sig in title.lower() for sig in JUNK_TITLE_SIGNALS):
        return None
    if item.get("Result Type") not in ("Official Website", "Government"):
        return None

    # ── Fetch homepage ─────────────────────────────────────────────────────
    homepage = _normalize_homepage(url)

    # Domain dedup — check before fetching to avoid wasted requests
    try:
        netloc = _strip_www(urlparse(homepage).netloc)
    except Exception:
        return None

    with seen_domains_lock:
        if netloc in seen_domains:
            return None
        seen_domains.add(netloc)

    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        resp     = session.get(homepage, timeout=REQUEST_TIMEOUT, allow_redirects=True, verify=False)
        html     = resp.text
        status   = resp.status_code
        homepage = _normalize_homepage(resp.url)
    except Exception:
        return None

    if status in (403, 404, 429, 503):
        return None

    html_lower = html.lower()
    if any(sig in html_lower for sig in BLOCKED_SIGNALS):
        return None

    soup      = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True).lower()

    if len(page_text) < 400:
        return None

    # ── Scoring — identical logic to your original ─────────────────────────
    org_score         = 0
    child_access_score = 0
    junk_score        = 0
    reasons           = []

    # Category signals
    category_hits = sum(1 for s in category_signals if s.lower().strip() and s.lower() in page_text)
    if category_hits >= 8:
        org_score += 4; reasons.append(f"{category_hits} category signals")
    elif category_hits >= 4:
        org_score += 2; reasons.append(f"{category_hits} category signals")

    # Location
    loc_hits = page_text.count(location.lower())
    if loc_hits == 0:
        junk_score += 3; reasons.append(f"No mention of '{location}'")
    elif loc_hits >= 2:
        org_score += 1; reasons.append(f"{loc_hits} location mentions")

    # NGO keywords
    hits = sum(1 for w in NGO_KEYWORDS if w in page_text)
    if hits >= 10:
        org_score += 5; reasons.append(f"{hits} NGO keywords")
    elif hits >= 6:
        org_score += 3; reasons.append(f"{hits} NGO keywords")

    # Collaboration
    collab_hits = sum(1 for s in COLLABORATION_SIGNALS if s in page_text)
    if collab_hits == 0:
        junk_score += 4; reasons.append("No collaboration signals")

    # Child signals
    child_hits = sum(1 for w in CHILD_NGO_SIGNALS if w in page_text)
    if child_hits >= 8:
        child_access_score += 5
    elif child_hits >= 4:
        child_access_score += 3

    education_hits = sum(1 for w in EDUCATION_SIGNALS if w in page_text)
    if education_hits >= 8:
        child_access_score += 4
    elif education_hits >= 4:
        child_access_score += 2

    service_hits = sum(1 for w in CHILD_SERVICE_SIGNALS if w in page_text)
    if service_hits >= 2:
        child_access_score += 4

    program_hits = sum(1 for w in CHILD_PROGRAMS if w in page_text)
    if program_hits >= 3:
        child_access_score += 4

    # Premium school penalty
    if sum(1 for w in PREMIUM_SCHOOL_KEYWORDS if w in page_text) >= 3:
        junk_score += 4; reasons.append("Premium/International school")

    # Business / SEO / Company instant reject
    if sum(1 for w in BUSINESS_SIGNALS if w in page_text) >= 2:
        return None
    if sum(1 for w in SEO_SIGNALS if w in page_text) >= 2:
        return None
    if sum(1 for w in COMPANY_SIGNALS if w in page_text) >= 3:
        return None

    # JSON-LD
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list): data = data[0]
            if any(t in str(data.get("@type","")) for t in ORG_SCHEMA_TYPES):
                org_score += 1; break
        except Exception:
            pass

    # og:site_name
    og = soup.find("meta", property="og:site_name")
    if og and isinstance(og.get("content"), str) and og["content"].strip():
        org_score += 1

    # Nav links
    nav_hits        = 0
    child_nav_hits  = 0
    page_hits       = set()
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").lower()
        text = a.get_text(" ", strip=True).lower()
        if any(kw in text for kw in ORG_NAV_KEYWORDS): nav_hits += 1
        if any(w in text or w in href for w in CHILD_NAV): child_nav_hits += 1
        for page in NGO_PAGES:
            if page in href or page in text: page_hits.add(page)

    if nav_hits >= 3:
        org_score += 1
    if len(page_hits) >= 6:
        org_score += 2
    elif len(page_hits) >= 3:
        org_score += 1
    if child_nav_hits >= 15:
        child_access_score += 5
    elif child_nav_hits >= 8:
        child_access_score += 4
    elif child_nav_hits >= 3:
        child_access_score += 3

    # Footer
    footer = soup.find("footer")
    if footer:
        ft = footer.get_text(" ", strip=True).lower()
        fh = sum(1 for w in FOOTER_KEYWORDS if w in ft)
        if fh >= 6:   org_score += 2
        elif fh >= 3: org_score += 1

    # Page title junk
    title_tag  = soup.find("title")
    page_title = title_tag.get_text(strip=True).lower() if title_tag else ""
    if any(x in page_title for x in BAD_TITLE):
        junk_score += 4
    if any(sig in page_text for sig in [
        "apply now", "scholarship deadline", "how to apply",
        "exam date", "list of ngos", "best ngos in india"
    ]):
        junk_score += 1

    # ── Decision ───────────────────────────────────────────────────────────
    final_score = org_score + (child_access_score // 3) - junk_score
    conditions  = sum([hits >= 8, child_nav_hits >= 3, program_hits >= 3])

    if final_score >= 8 and conditions >= 2:
        validation = "Valid"
    elif final_score >= 8:
        validation = "Unsure"
    else:
        return None   # Invalid — drop silently

    print(f"  [Validator] {validation}: {title[:55]} (score={final_score})")

    return {
        "Category":   item["Category"],
        "Location":   item["Location"],
        "Title":      title,
        "URL":        url,
        "Result Type": item["Result Type"],
        "Validation": validation,
        "Homepage":   homepage,
        "Html":       html,
    }


def run_validator_worker(url_queue, valid_queue, category_signals, location,
                          seen_domains, seen_domains_lock,
                          stop_event, search_done_event):
    """
    Runs in its own thread. Pulls from url_queue, validates,
    pushes Valid/Unsure results to valid_queue.
    Stops when search is done AND url_queue is empty.
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        pending = []

        def _drain_done():
            done = [f for f in pending if f.done()]
            for f in done:
                pending.remove(f)
                try:
                    result = f.result()
                    if result:
                        valid_queue.put(result)
                except Exception as e:
                    print(f"  [Validator] Worker error: {e}")

        while True:
            _drain_done()

            try:
                item = url_queue.get(timeout=0.2)
            except Exception:
                if search_done_event.is_set() and url_queue.empty():
                    break
                if stop_event.is_set():
                    break
                continue

            if stop_event.is_set():
                break

            f = pool.submit(
                validate_one, item, category_signals, location,
                seen_domains, seen_domains_lock
            )
            pending.append(f)

        # drain remaining futures
        for f in pending:
            try:
                result = f.result()
                if result:
                    valid_queue.put(result)
            except Exception as e:
                print(f"  [Validator] Final drain error: {e}")

    print("  [Validator] Done.")