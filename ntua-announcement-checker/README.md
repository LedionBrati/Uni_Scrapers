# NTUA Announcement Checker

A lightweight Python script that checks whether university department websites have published a specific announcement, by scraping their announcement pages and searching for keywords.

Built for volunteer use at **Get Involved**, a Greek non-profit focused on financial and sustainability literacy.

---

## How it works

The script fetches the announcement pages of a predefined list of NTUA (National Technical University of Athens) departments, strips the HTML, and searches for a set of keywords. It then prints a simple status report.

```
✅  School of Architecture              | POSTED
    └─ match: «Sustainable Future V»  @  https://www.arch.ntua.gr/...
❌  School of Mechanical Engineering    | NOT FOUND
⚠️   MSc Geoinformatics                 | connection error
```

---

## Setup

```bash
pip install requests beautifulsoup4
python check_announcements.py
```

---

## Customization

Open `check_announcements.py` and edit the two variables at the top:

**Keywords** — what to look for on each page:
```python
KEYWORDS = [
    "Sustainable Future V",
    "Get Involved",
    "ESG Becomes Strategy",
]
```

**Schools** — which pages to check:
```python
SCHOOLS = {
    "School of Architecture": [
        "https://www.arch.ntua.gr/index.php/anakoinosi_grammatia/",
    ],
    # add more departments as needed
}
```

Each department accepts a list of URLs — the script tries them in order and stops as soon as it finds a match.

---

## Use cases

- Verifying that secretariats have published a forwarded announcement
- Monitoring multiple department pages for any new content
- Reusable for any future event — just swap the keywords

---

## Notes

Some NTUA websites use self-signed SSL certificates. The script disables SSL verification for these requests (`verify=False`) and suppresses the related warnings. This is intentional and only affects outbound requests to known university domains.
