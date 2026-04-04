"""
Temporary DOM inspection script.
Saves rendered HTML of each department page to inspect/ folder.
"""
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

START_URLS = [
    ("oikonomikis",  "https://www.unipi.gr/tmima-oikonomikis-epistimis/"),
    ("ode",          "https://www.unipi.gr/tmima-organosis-kai-dioikisis-epixirisewn/"),
    ("des",          "https://www.des.unipi.gr/el/contact"),
    ("tourism",      "http://tourism.unipi.gr/contact/"),
    ("nautiliakon",  "https://www.unipi.gr/tmima-nautiliakwn-spoudwn/"),
    ("viomixanikis", "https://www.unipi.gr/tmima-viomixanikis-dioikisis/"),
    ("bankfin",      "https://bankfin.unipi.gr/contact"),
    ("statistikis",  "https://www.unipi.gr/tmima-statistikis-kai-asfalistikis-epistimis/"),
    ("cs",           "https://cs.unipi.gr/grammateia/"),
    ("ds",           "https://www.ds.unipi.gr/secretary/"),
]

os.makedirs("inspect", exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
    context = browser.new_context(
        locale="el-GR",
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    )
    page = context.new_page()

    for slug, url in START_URLS:
        print(f"Fetching {slug}...")
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            html = page.content()
            with open(f"inspect/{slug}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  Saved inspect/{slug}.html ({len(html)//1024}KB)")
        except PWTimeout:
            print(f"  TIMEOUT: {url}")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(1)

    browser.close()
print("Done.")
