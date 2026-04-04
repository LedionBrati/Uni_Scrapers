"""
UNIPI Secretariat Scraper — Site-Specific Configuration Map edition
Uses Playwright to render each page, then applies per-site CSS selectors
to extract secretariat working hours precisely.
Output: unipi_secretariats.csv
"""

import re
import csv
import time
from urllib.parse import unquote
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

TIMEOUT_MS = 20_000   # ms – page navigation timeout
WAIT_MS    = 2_500    # ms – settle time after load for JS rendering
DELAY      = 1.5      # seconds between requests (be polite)

OUTPUT_FILE = "unipi_secretariats.csv"
CSV_COLUMNS = ["Department", "Phone Number", "Email Address", "Working Hours", "Site URL"]

START_URLS = [
    ("Οικονομικής Επιστήμης",                        "https://www.unipi.gr/tmima-oikonomikis-epistimis/"),
    ("Οργάνωσης & Διοίκησης Επιχειρήσεων",           "https://www.unipi.gr/tmima-organosis-kai-dioikisis-epixirisewn/"),
    ("Διεθνών και Ευρωπαϊκών Οικονομικών Σπουδών",   "https://www.des.unipi.gr/el/contact"),
    ("Τουριστικών Σπουδών",                           "http://tourism.unipi.gr/contact/"),
    ("Ναυτιλιακών Σπουδών",                           "https://www.unipi.gr/tmima-nautiliakwn-spoudwn/"),
    ("Βιομηχανικής Διοίκησης",                        "https://www.unipi.gr/tmima-viomixanikis-dioikisis/"),
    ("Χρηματοοικονομικής",                            "https://bankfin.unipi.gr/contact"),
    ("Στατιστικής",                                   "https://www.unipi.gr/tmima-statistikis-kai-asfalistikis-epistimis/"),
    ("Πληροφορικής",                                  "https://cs.unipi.gr/grammateia/"),
    ("Ψηφιακών Συστημάτων",                           "https://www.ds.unipi.gr/secretary/"),
]

# -------------------------------------------------------------------
# Site-Specific Configuration Map
#
# Keys are URL substrings used to match the current page URL.
# Each entry may contain:
#   hours_selector  – CSS selector for the element(s) holding hours text.
#                     If None, hours are not published on this page.
#   keyword         – A Greek word that must appear in a matched element
#                     to confirm it is the secretariat hours (not unrelated
#                     text that happens to match the selector).
#   js_before       – Optional JS snippet evaluated in the page before
#                     extraction (e.g. to open collapsed <details> accordions).
# -------------------------------------------------------------------

SITE_CONFIG = {
    # Hours sit inside a collapsed Elementor <details> accordion
    # labelled "Διοικητικό Προσωπικό". We open ALL details elements
    # via JS, then target the paragraph that mentions working days.
    "tmima-oikonomikis-epistimis": {
        "js_before": "document.querySelectorAll('details').forEach(d => d.open = true)",
        "hours_selector": ".e-n-accordion-item .elementor-widget-text-editor p",
        "keyword": "δευτέρα",
    },

    # DOM inspection found no hours published on this page.
    "tmima-organosis-kai-dioikisis": {
        "hours_selector": None,
    },

    # DOM inspection found no hours published on this page.
    "des.unipi.gr": {
        "hours_selector": None,
    },

    # Hours are in a plain <p> inside an Elementor text widget.
    # The paragraph contains other text too, so use sentence_keyword
    # to extract only the sentence(s) that mention working days.
    "tourism.unipi.gr": {
        "hours_selector": ".elementor-widget-text-editor p",
        "keyword": "γραμματεία",
        "sentence_keyword": "δευτέρα",
    },

    # DOM inspection found no hours published on this page.
    "tmima-nautiliakwn-spoudwn": {
        "hours_selector": None,
    },

    # DOM inspection found no hours published on this page.
    "tmima-viomixanikis-dioikisis": {
        "hours_selector": None,
    },

    # DOM inspection found no hours published on this page.
    "bankfin.unipi.gr": {
        "hours_selector": None,
    },

    # DOM inspection found no hours published on this page.
    "tmima-statistikis": {
        "hours_selector": None,
    },

    # Hours are in a <p> inside a WPBakery text column widget.
    # The paragraph also contains building address text; extract only
    # the sentence that mentions working days.
    "cs.unipi.gr": {
        "hours_selector": ".wpb_text_column .wpb_wrapper p",
        "keyword": "δευτέρα",
        "sentence_keyword": "δευτέρα",
    },

    # Hours are in a <p> directly inside .entry-content.
    # The paragraph also contains address text, so extract only the
    # sentence that mentions working days.
    "ds.unipi.gr": {
        "hours_selector": ".entry-content p",
        "keyword": "γραμματεί",
        "sentence_keyword": "δευτέρα",
    },
}


def get_site_config(url: str) -> dict:
    """Return the SITE_CONFIG entry whose key is a substring of the given URL."""
    for key, config in SITE_CONFIG.items():
        if key in url:
            return config
    return {"hours_selector": None}


# -------------------------------------------------------------------
# Regex patterns
# -------------------------------------------------------------------

# Greek landline / mobile: 210xxxxxxx, +30 210 xxx xxxx, 69xxxxxxxx, etc.
PHONE_RE = re.compile(
    r'(?:\+30[\s\-\.]?)?'
    r'(?:2\d{3}|69\d{2})'
    r'[\s\-\.]?\d{3}'
    r'[\s\-\.]?\d{4}',
    re.ASCII,
)

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# -------------------------------------------------------------------
# Extraction helpers
# -------------------------------------------------------------------

def normalise_phone(raw: str) -> str:
    """URL-decode, strip non-digit/+ chars, reformat as +30 XXXX XXXXXX."""
    decoded = unquote(raw).strip()
    digits_only = re.sub(r'[^\d+]', '', decoded)
    if digits_only.startswith("0030"):
        digits_only = "+" + digits_only[2:]
    elif digits_only.startswith("0") and not digits_only.startswith("+"):
        digits_only = digits_only.lstrip("0")
    core = digits_only.lstrip("+")
    if digits_only.startswith("+30"):
        core = digits_only[3:]
    if len(core) != 10:
        return ""
    return f"+30 {core[:4]} {core[4:]}"


def extract_phones(soup: BeautifulSoup, raw_text: str) -> str:
    phones = []
    for tag in soup.select("a[href^='tel:']"):
        num = normalise_phone(tag["href"].replace("tel:", ""))
        if num and num not in phones:
            phones.append(num)
    decoded_text = unquote(raw_text)
    for match in PHONE_RE.findall(decoded_text):
        num = normalise_phone(match)
        if num and num not in phones:
            phones.append(num)
    return "; ".join(phones)


def extract_emails(soup: BeautifulSoup, raw_text: str) -> str:
    emails = []
    for tag in soup.select("a[href^='mailto:']"):
        addr = tag["href"].replace("mailto:", "").strip().split("?")[0]
        if addr and addr not in emails:
            emails.append(addr)
    for addr in EMAIL_RE.findall(raw_text):
        if addr not in emails:
            emails.append(addr)
    return "; ".join(emails)


def extract_sentence(text: str, keyword: str) -> str:
    """
    Split text into sentences and return only those containing keyword.
    Sentences are split on '.', '!', '?', or newlines.
    """
    sentences = re.split(r'(?<=[.!?])\s+|\n', text)
    matches = [s.strip() for s in sentences if keyword in s.lower() and len(s.strip()) > 10]
    return " ".join(matches)


def extract_hours_by_config(page, url: str) -> str:
    """
    Use the site-specific config to extract working hours.
    1. Optionally run JS to expose hidden content (e.g. expand accordions).
    2. Query all elements matching hours_selector.
    3. Filter by keyword to confirm the right element.
    4. If sentence_keyword is set, extract only the relevant sentence(s)
       from the element text rather than the full block.
    5. Return cleaned text of the best match.
    """
    config = get_site_config(url)
    selector = config.get("hours_selector")

    if not selector:
        return ""

    # Run any pre-extraction JS (e.g. open collapsed details)
    js = config.get("js_before")
    if js:
        try:
            page.evaluate(js)
            page.wait_for_timeout(500)
        except Exception:
            pass

    keyword          = config.get("keyword", "").lower()
    sentence_keyword = config.get("sentence_keyword", "").lower()

    try:
        elements = page.query_selector_all(selector)
    except Exception:
        return ""

    for el in elements:
        try:
            text = el.inner_text().strip()
        except Exception:
            continue
        if not text:
            continue
        # Must contain the confirmation keyword
        if keyword and keyword not in text.lower():
            continue
        # Clean excess whitespace
        text = re.sub(r'\s{2,}', ' ', text).strip()
        # If a sentence-level keyword is set, extract only matching sentences
        if sentence_keyword:
            extracted = extract_sentence(text, sentence_keyword)
            return extracted if extracted else text
        return text

    return ""


# -------------------------------------------------------------------
# Core scrape function
# -------------------------------------------------------------------

def scrape_department(page, name: str, url: str) -> dict:
    row = {
        "Department":    name,
        "Phone Number":  "",
        "Email Address": "",
        "Working Hours": "",
        "Site URL":      url,
    }

    print(f"  Scraping: {name}")

    try:
        page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT_MS)
    except PWTimeout:
        print(f"    [TIMEOUT] {url}")
        return row
    except Exception as exc:
        print(f"    [ERROR]   {url}: {exc}")
        return row

    # Extract hours via site-specific config (before decomposing the DOM)
    row["Working Hours"] = extract_hours_by_config(page, url)

    # Parse full rendered HTML for phones and emails
    html = page.content()
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    raw_text = soup.get_text(separator="\n", strip=True)

    row["Phone Number"]  = extract_phones(soup, raw_text)
    row["Email Address"] = extract_emails(soup, raw_text)

    return row


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main():
    results = []

    print("=" * 60)
    print("UNIPI Secretariat Scraper (Site-Specific Config Map)")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"],
        )
        context = browser.new_context(
            locale="el-GR",
            ignore_https_errors=True,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        for i, (name, url) in enumerate(START_URLS):
            row = scrape_department(page, name, url)
            results.append(row)
            if i < len(START_URLS) - 1:
                time.sleep(DELAY)

        browser.close()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 60)
    print(f"Done. Results saved to: {OUTPUT_FILE}")
    print("=" * 60)

    print(f"\n{'Department':<45} {'Phone':<22} {'Email':<35} {'Hours'}")
    print("-" * 130)
    for r in results:
        hours = r['Working Hours'] or "— not published —"
        print(
            f"{r['Department']:<45} "
            f"{r['Phone Number'][:20]:<22} "
            f"{r['Email Address'][:33]:<35} "
            f"{hours[:45]}"
        )


if __name__ == "__main__":
    main()
