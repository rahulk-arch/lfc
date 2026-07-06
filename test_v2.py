import requests
from bs4 import BeautifulSoup
import re
import json
import urllib3
from urllib.parse import urljoin, urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def strip_www(netloc: str) -> str:
    netloc = netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def extract_organizations(validated_results):

    JUNK_ORG_SIGNALS = [
        "just a moment", "access denied", "403", "404", "429",
        "scholarships", "top 10", "top 50", "list of",
        "press release", "recruitment", "job alert", "page not found",
    ]

    def is_junk_org(name: str) -> bool:
        n = name.lower()
        return any(s in n for s in JUNK_ORG_SIGNALS)

    existing_domains = set()
    count = 0
    organizations = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    for item in validated_results:

        category = item["Category"]
        url = item["URL"]
        result_type = item["Result Type"]
        validation = item["Validation"]
        homepage = item["Homepage"]
        html = item.get("Html", "")

        if not url or url.lower().endswith(".pdf"):
            continue
        if validation != "Valid":
            continue
        if result_type not in ["Official Website", "Government"]:
            continue
        if not homepage:
            continue

        parsed = urlparse(homepage)
        homepage = f"{parsed.scheme}://{parsed.netloc}"
        domain = strip_www(parsed.netloc)

        if domain in existing_domains:
            print(f"[DUPLICATE] {domain} — skipping")
            continue

        # Reuse HTML from validator — only refetch if missing (shouldn't normally happen)
        if not html:
            print(f"  No cached HTML, refetching: {homepage}")
            try:
                response = requests.get(homepage, headers=headers, timeout=15, verify=False)
                if response.status_code != 200:
                    continue
                html = response.text
            except Exception as e:
                print(f"  Failed: {e}")
                continue
        else:
            print(f"Parsing (cached): {homepage}")

        html_lower = html.lower()
        if any(sig in html_lower for sig in [
            "just a moment", "checking your browser",
            "access denied", "enable javascript and cookies"
        ]):
            print(f"  Blocked page — skipping")
            continue

        soup = BeautifulSoup(html, "html.parser")

        organization = ""

        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, list):
                    data = data[0]
                if isinstance(data, dict):
                    name = data.get("name") or data.get("legalName")
                    org_type = str(data.get("@type", ""))
                    if name and any(t in org_type for t in [
                        "Organization", "NGO", "GovernmentOrganization",
                        "EducationalOrganization", "Corporation"
                    ]):
                        organization = name.strip()
                        break
            except Exception:
                pass

        if not organization:
            meta = soup.find("meta", property="og:site_name")
            if meta:
                content = meta.get("content", "")
                if isinstance(content, (list, tuple)):
                    content = " ".join(content)
                if str(content).strip():
                    organization = str(content).strip()

        if not organization and soup.title:
            raw = soup.title.text.strip()
            raw = re.split(r"\s*[\|\-–—]\s*", raw)[0].strip()
            organization = raw

        if not organization:
            # domain fallback — strip TLD, not just hyphens
            organization = domain.split(".")[0].replace("-", " ").title()

        if is_junk_org(organization):
            print(f"  Junk org name: {organization} — skipping")
            continue

        instagram = linkedin = facebook = youtube = email = phone = ""

        SOCIAL_SKIP = [
            "share", "intent", "sharer", "/reel/", "/p/",
            "watch?", "playlist?", "login", "signup",
            "?subject=", "?body=",
        ]

        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            if isinstance(href, (list, tuple)):
                href = href[0] if href else ""
            href = str(href).strip()
            link = urljoin(homepage, href)
            lower = link.lower()

            if any(s in lower for s in SOCIAL_SKIP):
                continue

            if "instagram.com" in lower and not instagram:
                instagram = link.rstrip("/")
            elif "facebook.com" in lower and not facebook:
                facebook = link.rstrip("/")
            elif "linkedin.com" in lower and not linkedin:
                linkedin = link.rstrip("/")
            elif ("youtube.com" in lower or "youtu.be" in lower) and not youtube:
                youtube = link.rstrip("/")
            elif lower.startswith("mailto:") and not email:
                email = href.replace("mailto:", "").split("?")[0].strip()
            elif lower.startswith("tel:") and not phone:
                phone = href.replace("tel:", "").strip()

        page_text = soup.get_text(" ", strip=True)

        if not email:
            emails = re.findall(
                r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", page_text
            )
            for e in emails:
                if not any(bad in e.lower() for bad in ["example", "yourdomain", "@sentry", "@2x"]):
                    email = e
                    break

        if not phone:
            phones = re.findall(
                r'(?:\+91[\s\-]?)?[6-9]\d{9}\b|0\d{2,4}[\s\-]\d{6,8}', page_text
            )
            if phones:
                phone = phones[0].strip()

        organizations.append({
            "Organization": organization,
            "Website": homepage,
            "Instagram": instagram,
            "LinkedIn": linkedin,
            "Facebook": facebook,
            "YouTube": youtube,
            "Email": email,
            "Phone": phone,
            "Category": category,
        })

        existing_domains.add(domain)
        count += 1
        print(f"  Saved: {organization}")

    print(f"\nDone! Total saved: {count}")
    return organizations