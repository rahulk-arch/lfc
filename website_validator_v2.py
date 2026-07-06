import json
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def validate_websites(search_results):

    # Config

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    REQUEST_TIMEOUT = 6

    session = requests.Session()
    session.headers.update(HEADERS)

    # STEP 1: Domain blacklist → instant Invalid

    INVALID_DOMAINS = {
        "vajiramandravi.com", "behtarlife.com",
        "advance-africa.com", "opportunitydesk.org", "scholars4dev.com",
        "afterschoolafrica.com", "influencers.feedspot.com",
        "influvera.com", "socialnative.com", "grynow.in",
        "indiacsr.in", "impriindia.com", "civilsdaily.com",
        "educationforallinindia.com", "teachers.institute",
        "narayanseva.org", "indianbureaucracy.com",
        "sitelike.org", "danamojo.org", "catalog.in",
        "legalonus.com", "writinglaw.com", "pathlegal.in",
        "gojuris.in", "dokumen.pub",
        "bing.com", "education21.in",
        "highereducationdigest.com",
        "globaleducationnews.org",
        "pdfcoffee.com",
        "epdf.pub", "epdf.tips",
        "slideshare.net",
        "scarymommy.com", "positive-parenting-ally.com",
        "theindianpublisher.com", "justbaazaar.com",
        "indiamart.com", "justdial.com", "sulekha.com", "tradeindia.com",
        "exportersindia.com", "dir.indiamart.com",
        "ok.ru", "lootbar.com", "airofficesguides.com",
        "cpduk.co.uk", "ropergulf.nt.gov.au", "delcoresources.org",
    }

    # STEP 2: URL pattern blacklist → instant Invalid

    INVALID_URL_PATTERNS = [
        "/directory/",
        "/directories/",
        "/listing/",
        "/list/",
        "/ngo-list/",
        "/ngos/",
        "/top-ngos/",
        "/best-ngos/",
        "/compare/",
        "/reviews/",
        "bing.com/aclick",          
        "/article", "/articles",
        "/blog", "/blogs",
        "/news",
        "/post/",
        "/story/",
        "/insights/",
        "/press-release",
        "/press_release",
        "/profileshow/",           
        "/panache/",
        "/gallery/",
        "/2020/", "/2021/", "/2022/", "/2023/", "/2024/", "/2025/",
        ".pdf",
        "/download",
        "/Errors/Error",    
        "/pages/",                
        "/past-edition",     
        "/event/",          
        "/category/",         
        "/tag/",                    
        "/wp-content/",          
        "/pub/",
        "/press/",
        "/top-100", "/top-50", "/top-10", "/best-of", "/best-50", "/best-10",
        "/best-ngos", "/best-nonprofits", "/best-foundations",
        "/list-of-ngos", "/list-of-nonprofits", "/list-of-foundations", "ngo-list", "nonprofit-list", "foundation-list",
    ]

    # STEP 3: Blocked page signals

    BLOCKED_SIGNALS = [
        "just a moment", "checking your browser", "attention required",
        "access denied", "enable javascript and cookies",
        "ddos protection", "ray id", "please wait while we verify",
    ]

    # STEP 4: Org-positive signals (page content)

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

    # STEP 5: Junk content signals


    JUNK_TITLE_SIGNALS = [
        "best ngos", "list of",
        "scholarships", "scholarship", "how to apply", "funding opportunities",
        "inspiring stories", "making a difference", "upsc", "ias notes",
        "study material", "exam preparation", "recruitment", "job alert",
        "just a moment", "access denied", "403 forbidden", "404",
        "press release", "news:", "| news", "latest news",
        "characters guide", "gta 6", 
        "quotes in hindi", "influencers in 2026", "top influencers",
        "alternatives", "sites like",
    ]

    
    # Helper: normalize to homepage
    

    def normalize_to_homepage(url: str):
        try:
            p = urlparse(url)
            scheme = p.scheme if p.scheme in ("http", "https") else "https"
            return f"{scheme}://{p.netloc}"
        except Exception:
            return url

    # Helper: check domain blacklist

    def is_blacklisted_domain(url: str) -> bool:
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return any(netloc == d or netloc.endswith("." + d) for d in INVALID_DOMAINS)
        except Exception:
            return False

    
    # Helper: check URL patterns

    def has_invalid_url_pattern(url: str) -> bool:
        url_lower = url.lower()
        return any(pat in url_lower for pat in INVALID_URL_PATTERNS)

    
    # Core validator

    def validate_url(url: str, title: str = "") -> tuple[str, str, str, str]:
        """
        Returns (result, homepage, reason, html)
        result  → "Valid" | "Invalid" | "Unsure"
        homepage → normalized homepage URL or ""
        reason  → short explanation
        html    → fetched HTML content or ""
        """

        # --- Step 1: Domain blacklist ---
        if is_blacklisted_domain(url):
            return "Invalid", "", "Blacklisted domain (news/blog/junk)", ""

        # --- Step 2: URL pattern ---
        if has_invalid_url_pattern(url):
            return "Invalid", "", "URL looks like article/ad/error page", ""
        # --- Step 3: Title check (before fetching) ---
        title_lower = title.lower()
        if any(sig in title_lower for sig in JUNK_TITLE_SIGNALS):
            return "Invalid", "", f"Junk title signal: {title[:60]}", ""

        # --- Step 4: Fetch homepage ---
        try:
            response = session.get(
                normalize_to_homepage(url),
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False
            )

            homepage = normalize_to_homepage(response.url)
            html = response.text
            status = response.status_code

        except Exception:
            return "Unsure", "", "Could not fetch homepage", ""

        if html is None:
            return "Unsure", "", f"Could not fetch (status={status})", ""

        if status in (403, 404, 429, 503):
            return "Unsure", "", f"HTTP {status}", ""

        html_lower = html.lower()

        # --- Step 5: Blocked page ---
        if any(sig in html_lower for sig in BLOCKED_SIGNALS):
            return "Unsure", homepage, "Cloudflare / access blocked", ""
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True).lower()

        org_score = 0
        junk_score = 0
        child_access_score = 0
        reasons = []

        # Very small pages are usually placeholders, redirects, or error pages
        if len(page_text) < 400:
            junk_score += 3
            reasons.append("Very little page content")
        
        CHILD_SERVICE_SIGNALS = [
            "learning centre",
            "learning center",
            "education centre",
            "education center",
            "bridge school",
            "after school",
            "school readiness",
            "community school",
            "child care centre",
        ]

        service_hits = sum(word in page_text for word in CHILD_SERVICE_SIGNALS)

        if service_hits >= 2:
            child_access_score += 4
            reasons.append(f"{service_hits} child service signals")

        EDUCATION_SIGNALS = [
            "school",
            "schools",
            "student",
            "students",
            "teacher",
            "teachers",
            "classroom",
            "primary school",
            "government school",
            "municipal school",
            "school children",
            "pre-school",
            "preschool",
            "primary school",
            "kindergarten",
            "play school",
        ]

        education_hits = sum(word in page_text for word in EDUCATION_SIGNALS)

        if education_hits >= 8:
            child_access_score += 4
            reasons.append(f"{education_hits} education signals")

        elif education_hits >= 4:
            child_access_score += 2
            reasons.append(f"{education_hits} education signals")

        CHILD_NGO_SIGNALS = [
            "child education",
            "child rights",
            "child protection",
            "child sponsorship",
            "children",
            "school children",
            "children we serve",
            "children enrolled",
            "children reached",
            "working with children",
            "children in our care",
            "slum children",
            "orphanage",
            "child care",
            "early childhood",
            "education for children",
            "child development",
        ]

        child_hits = sum(word in page_text for word in CHILD_NGO_SIGNALS)

        if child_hits >= 8:
            child_access_score += 5
            reasons.append(f"{child_hits} child-focus signals")

        elif child_hits >= 4:
            child_access_score += 3
            reasons.append(f"{child_hits} child-focus signals")


        CHILD_PROGRAMS = [
            "our programs",
            "our programme",
            "our programmes",
            "our initiatives",
            "our projects",
            
            "learning centre",
            "learning center",
            "bridge school",
            "community school",
            "after school",
            "school readiness",
            "underprivileged children",
            "education for underprivileged",
            "education for underserved",
            "street children",
            "slum children",
            "marginalized children",
            "out-of-school children",
            "education access",
            "school enrollment",
            "bridge learning",

            # Children
            "children",
            "child education",
            "child development",
            "child rights",
            "child protection",
            "child welfare",
            "child sponsorship",
            "sponsor a child",
            "early childhood",
            "balwadi",
            "anganwadi",


            # Residential care
            "hostel",
            "residential home",
            "child care centre",
            "child care center",
            "orphanage",

            # Skill development
            "life skills",
        ]

        program_hits = sum(word in page_text for word in CHILD_PROGRAMS)

        if program_hits >= 3:
            child_access_score += 4
            reasons.append(f"{program_hits} child program signals")


        PREMIUM_SCHOOL_KEYWORDS = [
            "international school",
            "ib curriculum",
            "cambridge curriculum",
            "cambridge assessment",
            "igcse",
            "ibdp",
            "boarding school",
            "world school",
            "global school",
            "residential campus",
            "admission open",
            "admission enquiry",
            "fee structure",
            "tuition fee",
            "online admission",
    ]

        premium_hits = sum(word in page_text for word in PREMIUM_SCHOOL_KEYWORDS)

        if premium_hits >= 3:
            junk_score += 4
            reasons.append("Premium/International school")


    # Business / Finance website  
        BUSINESS_SIGNALS = [
            "mutual fund",
            "insurance",
            "loan",
            "banking",
            "stock market",
            "investor relations",
            "shareholders",
            "our products",
            "our services",
            "customer support",
        ]

        business_hits = sum(word in page_text for word in BUSINESS_SIGNALS)

        if business_hits >= 2:
            return "Invalid", homepage, "Business / Finance website", ""

    # SEO / Guest Posting website  

        SEO_SIGNALS = [
            "guest post",
            "guest posting",
            "write for us",
            "submit article",
            "submit guest post",
            "advertise with us",
            "sponsored post",
            "become a contributor",
            "accepting guest posts",
        ]

        seo_hits = sum(word in page_text for word in SEO_SIGNALS)

        if seo_hits >= 2:
            return "Invalid", homepage, "SEO / Guest Posting website", ""

    # Company Website  

        COMPANY_SIGNALS = [
            "investor relations",
            "shareholders",
            "corporate governance",
            "quarterly results",
            "our products",
            "our services",
            "business units",
        ]

        company_hits = sum(word in page_text for word in COMPANY_SIGNALS)

        if company_hits >= 3:
            return "Invalid", homepage, "Corporate / Company website", ""

    # Collaboration Signals  

        COLLABORATION_SIGNALS = [
            "donate",
            "donate now",
            "volunteer",
            "get involved",
            "our work",
            "our impact",
            "our mission",
            "our vision",
            "our programs",
            "our projects",
            "campaigns",
            "beneficiaries",
            "our causes",
            "support us",
            "partner with us",
            "who we are",
        ]

        collaboration_hits = sum(signal in page_text for signal in COLLABORATION_SIGNALS)

        if collaboration_hits == 0:
            junk_score += 4
            reasons.append("No collaboration signals")

        # Homepage title check
        title_tag = soup.find("title")
        page_title = title_tag.get_text(" ", strip=True).lower() if title_tag else ""

        BAD_TITLE = [
            "directory",
            "blog",
            "article",
            "list of",
            "top 10",
            "top 20",
            "top 50",
            "top 100",
        ]

        matched = [x for x in BAD_TITLE if x in page_title]

        if matched:
            junk_score += 4
            reasons.append(f"BAD TITLE matched: {matched}")

        NGO_KEYWORDS = [
            "foundation",
            "trust",
            "society",
            "ngo",
            "nonprofit",
            "non profit",
            "donate",
            "volunteer",
            "mission",
            "impact",
            "community",
            "education",
            "health",
            "livelihood",
            "children",
            "annual report",
            "financial",
            "csr",
            "governance",
            "transparency",
        ]

        hits = 0

        for word in NGO_KEYWORDS:
            if word in page_text:
                hits += 1

        if hits >= 10:
            org_score += 5
            reasons.append(f"{hits} NGO keywords found")
        elif hits >= 6:
            org_score += 3
            reasons.append(f"{hits} NGO keywords found")
        
        BLOG_SIGNALS = [
            "leave a reply",
            "my blog",
            "my journey",
            "subscribe to my blog",
        ]

        blog_hits = 0

        for signal in BLOG_SIGNALS:
            if signal in page_text:
                blog_hits += 1

        if blog_hits >= 3:
            junk_score += 2
            reasons.append(f"{blog_hits} personal blog signals")




        # JSON-LD Organization type → strong positive
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, list):
                    data = data[0]
                schema_type = str(data.get("@type", ""))
                if any(t in schema_type for t in ORG_SCHEMA_TYPES):
                    org_score += 1
                    reasons.append(f"JSON-LD type={schema_type}")
                    break
            except Exception:
                pass

        # og:site_name present → mild positive
        og_site = soup.find("meta", property="og:site_name")

        if og_site:
            content = og_site.get("content")

            if isinstance(content, str) and content.strip():
                org_score += 1
                reasons.append("og:site_name present")

        # Nav links matching org keywords
        nav_hits = 0
        for a in soup.find_all("a", href=True):
            link_text = a.get_text(strip=True).lower()
            if any(kw in link_text for kw in ORG_NAV_KEYWORDS):
                nav_hits += 1
        if nav_hits >= 3:
            org_score += 1
            reasons.append(f"{nav_hits} org nav links")

        # Footer copyright → positive
        footer = soup.find("footer")

        if footer:

            footer_text = footer.get_text(" ", strip=True).lower()

            footer_hits = 0

            FOOTER_KEYWORDS = [

                "annual report",
                "financial",
                "financials",
                "governance",
                "transparency",
                "80g",
                "12a",
                "fcra",
                "donate",
                "volunteer",
                "csr",
                "impact",
                "privacy policy",
                "terms of use",
                "contact",
                "about us",
            ]

            for word in FOOTER_KEYWORDS:
                if word in footer_text:
                    footer_hits += 1

            if footer_hits >= 6:
                org_score += 2
                reasons.append(f"{footer_hits} organization footer signals")

            elif footer_hits >= 3:
                org_score += 1
                reasons.append(f"{footer_hits} organization footer signals")

            elif "©" in footer_text:
                org_score += 1
                reasons.append("Footer copyright")



        # Contact page or About page exists
        NGO_PAGES = [
            "about",
            "contact",
            "donate",
            "volunteer",
            "program",
            "programs",
            "project",
            "projects",
            "education program",
            "education programmes",
            "child sponsorship",
            "impact",
            "our-work",
            "what-we-do",
            "financial",
            "annual-report",
            "governance",
            "board",
            "team",
            "leadership",
            "partner",
            "partners",
        ]

        page_hits = set()
        child_nav_hits =0

        CHILD_NAV = [
            "child rights",
            "child protection",
            "child sponsorship",
            "early childhood",
            "bridge school",
            "after school",
            "school children",
            "community school",
            "government school",
            "municipal school",
            "anganwadi",
            "orphanage",
            "child care",
        ]

        for a in soup.find_all("a", href=True):

            href = a.get("href")

            if not isinstance(href, str):
                href = ""

            href = href.lower()

            text = a.get_text(" ", strip=True).lower()

            # Child navigation signals
            if any(word in text for word in CHILD_NAV) or any(word in href for word in CHILD_NAV):
                child_nav_hits += 1

            # NGO navigation signals
            for page in NGO_PAGES:
                if page in href or page in text:
                    page_hits.add(page)

        if len(page_hits) >= 6:
            org_score += 2
            reasons.append(f"{len(page_hits)} organization pages found")

        elif len(page_hits) >= 3:
            org_score += 1
            reasons.append(f"{len(page_hits)} organization pages found")

        if child_nav_hits >= 15:
            child_access_score += 5
            reasons.append(f"{child_nav_hits} child navigation links")

        elif child_nav_hits >= 8:
            child_access_score += 4
            reasons.append(f"{child_nav_hits} child navigation links")

        elif child_nav_hits >= 3:
            child_access_score += 3
            reasons.append(f"{child_nav_hits} child navigation links")

        # Page title junk check
        title_tag = soup.find("title")
        page_title = title_tag.get_text(strip=True).lower() if title_tag else ""
        page_title = page_title.strip()

        if (
            page_title.startswith("top 10")
            or page_title.startswith("top 20")
            or page_title.startswith("top 50")
            or page_title.startswith("top 100")
            or page_title.startswith("best ")
            or page_title.startswith("list of")
        ):
            junk_score += 4
            reasons.append("Directory/List page title")

        elif any(sig in page_title for sig in JUNK_TITLE_SIGNALS):
            junk_score += 3
            reasons.append(f"Junk page title: {page_title[:50]}")

        # Junk content signals in body
        junk_body_signals = [
            "apply now", "scholarship deadline", "eligibility criteria",
            "how to apply", "application form", "exam date", "list of ngos",
            "best ngos in india",
        ]
        for sig in junk_body_signals:
            if sig in page_text:
                junk_score += 1
                reasons.append(f"Body signal: '{sig}'")
                break  # one is enough

        # --- Step 7: Decision ---

        # --- Step 7: Decision ---
        final_score = org_score + (child_access_score // 3) - junk_score
        reasons.append(f"Org={org_score} Child={child_access_score} Junk={junk_score} Final={final_score}")

        # Strong NGO website
        conditions = 0

        if hits >= 8:
            conditions += 1

        if child_nav_hits >= 3:
            conditions += 1

        if program_hits >= 3:
            conditions += 1

        if final_score >= 8 and conditions >= 2:
            return "Valid", homepage, " | ".join(reasons), html

        # Looks promising but not enough confidence
        elif final_score >= 8:
            return "Unsure", homepage, " | ".join(reasons), html

        # Everything else
        else:
            return "Invalid", homepage, " | ".join(reasons), html


    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    MAX_WORKERS = 15  # start here; raise to 12-15 if stable, lower if you see lots of timeouts/blocks

    def strip_www(netloc: str) -> str:
        netloc = netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc

    # --- replace from here down ---

    to_process = []
    for row_idx, item in enumerate(search_results, start=1):
        result_type = item["Result Type"]
        url = item["URL"]

        if result_type not in ("Official Website", "Government"):
            continue
        if not url:
            continue

        to_process.append((row_idx, item))

    print(f"Validating {len(to_process)} URLs with {MAX_WORKERS} workers...")

    def process_item(row_idx, item):
        title = item["Title"]
        url = item["URL"]
        result, homepage, reason, html = validate_url(url, title)
        return {
            "Category": item["Category"],
            "Location": item["Location"],
            "Title": title,
            "URL": url,
            "Result Type": item["Result Type"],
            "Validation": result,
            "Homepage": homepage,
            "Reason": reason,
            "Html": html,
        }

    lock = threading.Lock()
    total = valid_count = invalid_count = unsure_count = 0
    validated_domains = set()
    validated_results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_item, idx, item): idx for idx, item in to_process}

        for future in as_completed(futures):
            try:
                row = future.result()
            except Exception as e:
                print(f"  Worker failed: {e}")
                continue

            with lock:
                total += 1

                # Duplicate-domain check happens here now (post-fetch), since
                # threads finish in unpredictable order
                if row["Validation"] == "Valid" and row["Homepage"]:
                    domain = strip_www(urlparse(row["Homepage"]).netloc)
                    if domain in validated_domains:
                        row["Validation"] = "Invalid"
                        row["Reason"] = "Duplicate domain (already validated this run)"
                        invalid_count += 1
                    else:
                        validated_domains.add(domain)
                        valid_count += 1
                elif row["Validation"] == "Invalid":
                    invalid_count += 1
                else:
                    unsure_count += 1

                validated_results.append(row)
                print(f"[{total}/{len(to_process)}] {row['Title'][:55]} -> {row['Validation']} | {row['Reason'][:150]}")

    print(f"\nDone!")
    print(f"  Valid:   {valid_count}")
    print(f"  Invalid: {invalid_count}")
    print(f"  Unsure:  {unsure_count}")
    print(f"  Total:   {total}")

    return validated_results