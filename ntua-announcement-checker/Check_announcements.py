

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import urllib3
import re
import sys
from datetime import datetime

# Πολλά πανεπιστημιακά sites έχουν θέματα με SSL - απενεργοποιούμε τις προειδοποιήσεις
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────────────────────────
# ΡΥΘΜΙΣΕΙΣ - ΑΛΛΑΞΕ ΑΥΤΑ ΓΙΑ ΚΑΘΕ ΝΕΑ ΑΝΑΚΟΙΝΩΣΗ
# ─────────────────────────────────────────────────────────────────

# Λέξεις-κλειδιά που πρέπει να βρεθούν στη σελίδα (αρκεί έστω μία)
KEYWORDS = [
    "Sustainable Future V",
    "Sustainable Future",
    "Get Involved",
    "Industry in Practice",
    # Πιο γενικές για περίπτωση που η γραμματεία άλλαξε λίγο τη διατύπωση
    "ESG Becomes Strategy",
]

# Οι σελίδες ανακοινώσεων που θες να ελέγξεις.
# Για κάθε σχολή βάζουμε ΟΛΑ τα πιθανά URLs (αρχική, ανακοινώσεις, εκδηλώσεις).
# Το script θα τσεκάρει όλα και θα αναφέρει αν βρέθηκε σε κάποιο.
SCHOOLS = {
    "Σχολή Αρχιτεκτόνων Μηχανικών": [
        "https://www.arch.ntua.gr/index.php/anakoinosi_grammatia/",
        "https://www.arch.ntua.gr/",
    ],
    "Σχολή Μηχανολόγων Μηχανικών": [
        "https://www.mech.ntua.gr/gr/links/docs",
        "https://www.mech.ntua.gr/gr/school-docs",
        "https://www.mech.ntua.gr/gr/",
    ],
    "Σχολή Ναυπηγών Μηχανολόγων Μηχανικών": [
        "https://www.naval.ntua.gr/",
        "http://old.naval.ntua.gr/general_news/",
    ],
    "Σχολή Αγρονόμων & Τοπογράφων": [
        "https://www.survey.ntua.gr/el/announcements",
        "https://www.survey.ntua.gr/",
    ],
    "ΔΠΜΣ Γεωπληροφορική": [
        "https://geoinformatics.ntua.gr/",
        "https://geoinformatics.ntua.gr/announcements/",
    ],
    "ΔΠΜΣ Τεχνο-Οικονομικά Συστήματα": [
        "https://technoeconomics.epu.ntua.gr/",
        "https://technoeconomics.epu.ntua.gr/news",
        "https://technoeconomics.epu.ntua.gr/en/news",
    ],
    "ΔΠΜΣ Επιστήμη & Τεχνολογία Υδατικών Πόρων": [
        "http://postgrad.hydro.ntua.gr/",
        "http://postgrad.hydro.ntua.gr/en/",
    ],
}

# ─────────────────────────────────────────────────────────────────
# ΛΟΓΙΚΗ - δεν χρειάζεται να αλλάξεις τίποτα παρακάτω
# ─────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_text(url: str, timeout: int = 15) -> str | None:
    """Κατεβάζει το URL και επιστρέφει μόνο το κείμενο (όχι HTML tags)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        r.raise_for_status()
        # Παίρνουμε μόνο το ορατό κείμενο
        soup = BeautifulSoup(r.text, "html.parser")
        # Αφαιρούμε scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Κανονικοποίηση whitespace
        text = re.sub(r"\s+", " ", text)
        return text
    except Exception as e:
        return None


def search_keywords(text: str, keywords: list[str]) -> str | None:
    """Επιστρέφει το πρώτο keyword που βρέθηκε ή None."""
    if not text:
        return None
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return kw
    return None


def check_school(name: str, urls: list[str]) -> dict:
    """Ελέγχει όλα τα URLs μιας σχολής. Αν βρει σε κάποιο, σταματάει."""
    for url in urls:
        text = fetch_text(url)
        if text is None:
            continue
        match = search_keywords(text, KEYWORDS)
        if match:
            return {"status": "found", "url": url, "match": match}
    # Αν δεν βρέθηκε σε καμία αλλά κάποια απάντησε:
    last_text = None
    for url in urls:
        if fetch_text(url) is not None:
            last_text = url
            break
    if last_text:
        return {"status": "not_found", "url": last_text, "match": None}
    return {"status": "error", "url": urls[0], "match": None}


def main():
    print("=" * 70)
    print(f"NTUA Announcement Checker — {datetime.now():%d/%m/%Y %H:%M}")
    print(f"Λέξεις-κλειδιά: {', '.join(KEYWORDS[:3])}...")
    print("=" * 70)

    found_count = 0
    missing_count = 0
    error_count = 0

    for name, urls in SCHOOLS.items():
        result = check_school(name, urls)
        if result["status"] == "found":
            found_count += 1
            print(f"✅  {name:<45} | ΑΝΑΡΤΗΘΗΚΕ")
            print(f"    └─ match: «{result['match']}»  @  {result['url']}")
        elif result["status"] == "not_found":
            missing_count += 1
            print(f"❌  {name:<45} | ΔΕΝ ΒΡΕΘΗΚΕ")
        else:
            error_count += 1
            print(f"⚠️   {name:<45} | σφάλμα σύνδεσης")

    print("=" * 70)
    print(f"Σύνολο: {found_count} αναρτημένες, "
          f"{missing_count} εκκρεμότητες, {error_count} σφάλματα")
    print("=" * 70)

    # Επιστρέφει exit code = αριθμός εκκρεμοτήτων (χρήσιμο για scripting)
    return missing_count


if __name__ == "__main__":
    sys.exit(main())
