
import csv
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path("profile").resolve())
MAX_KONTAKTE_PRO_FIRMA = 3
WARTEN_ZWISCHEN_FIRMEN = (5, 8)
DEFAULT_FIELDS = ["Firma 1", "Firma (Gesamt)", "Name"]

def position_relevant(pos_text):
    relevant_keywords = [
        "marketingleitung", "performance marketing", "online marketing", "brand management",
        "digitale projekte", "vertriebsleitung", "geschäftsleitung", "prokurist", "coo",
        "assistenz", "logistikleitung", "fuhrpark", "konfektionierung", "fertigungsleitung",
        "lagerleitung", "materialwirtschaft", "produktion", "qualitätsleiter", "it-", "cio",
        "edv", "controlling", "datenschutz", "recruiting", "buchhaltung", "e-commerce",
        "employer branding", "einkauf", "nachhaltigkeit", "business development",
        "customer success", "cto", "betriebsleitung", "strategie", "regulatory", "betriebsrat",
        "finanzen", "cfo", "produktmanagement", "ux", "design thinking", "digital transformation",
        "entwicklung", "versand"
    ]
    text = pos_text.lower()
    return any(kw in text for kw in relevant_keywords)

def scrape_leads(page, firma):
    suche = f'"{firma}" AND (HR OR Personal OR Marketing OR IT OR Geschäftsleitung OR Einkauf OR Finanzen OR Produktion)'
    page.goto("https://www.linkedin.com/sales/search/people")
    time.sleep(random.uniform(3.0, 5.0))
    
    try:
        suchfeld = page.locator("input[placeholder='Keywords für Suche']").first
        suchfeld.wait_for(state="visible", timeout=5000)
        suchfeld.fill("")
        for char in suche:
            suchfeld.type(char)
            time.sleep(random.uniform(0.05, 0.15))
        page.keyboard.press("Enter")
        time.sleep(random.uniform(4.0, 6.0))
    except:
        return []

    contacts = []
    scroll_count = 0
    seen_names = set()
    while scroll_count < 10 and len(contacts) < MAX_KONTAKTE_PRO_FIRMA:
        cards = page.locator("li.artdeco-list__item").all()
        for card in cards:
            try:
                card_text = card.inner_text().strip()
                lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                if len(lines) < 3:
                    continue
                name, position, firmaline = lines[0], lines[1], lines[2]
                if name in seen_names:
                    continue
                seen_names.add(name)

                if not position_relevant(position):
                    continue

                link_els = card.locator("a[href*='/sales/lead/']").all()
                link = ""
                for l in link_els:
                    href = l.get_attribute("href")
                    if href and "/sales/lead/" in href:
                        link = urljoin("https://www.linkedin.com", href)
                        break
                if not link:
                    continue

                contacts.append({
                    "Name": name,
                    "Position": position,
                    "LinkedIn Profil": link
                })
                if len(contacts) >= MAX_KONTAKTE_PRO_FIRMA:
                    break
            except:
                continue
        page.mouse.wheel(0, 1000)
        time.sleep(random.uniform(2.0, 3.0))
        scroll_count += 1
    return contacts

def start_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch_persistent_context(PROFILE_DIR, headless=False)
    page = browser.new_page()
    return p, browser, page

def choose_file_interactively():
    files = list(Path().glob("*.csv"))
    if not files:
        print("⚠️ Keine CSV-Dateien im aktuellen Ordner gefunden.")
        exit()
    print("📂 Verfügbare CSV-Dateien:")
    for idx, file in enumerate(files):
        print(f"{idx+1}: {file.name}")
    choice = input("Welche Datei soll verwendet werden? (Nummer eingeben): ")
    try:
        return str(files[int(choice)-1])
    except:
        print("❌ Ungültige Eingabe.")
        exit()

def detect_firmenspalte(headers):
    for feld in DEFAULT_FIELDS:
        if feld in headers:
            return feld
    print("\n🔎 Keine Standard-Firmenspalte gefunden.")
    print("Spaltenüberschriften:", headers)
    return input("Bitte gib den Spaltennamen für die Firmensuche ein: ").strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Pfad zur CSV-Datei", required=False)
    args = parser.parse_args()
    input_file = args.file or choose_file_interactively()
    
    with open(input_file, newline='', encoding='utf-8-sig') as infile:
        reader = csv.DictReader(infile)
        rows = list(reader)
        headers = reader.fieldnames.copy()
    
    firma_field = detect_firmenspalte(headers)
    basename = Path(input_file).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{basename}_salesnav_final.csv"

    for i in range(1, MAX_KONTAKTE_PRO_FIRMA + 1):
        for feld in ["Name", "Position", "LinkedIn Profil"]:
            new_field = f"{feld} {i}"
            if new_field not in headers:
                headers.append(new_field)

    p, browser, page = start_browser()
    page.goto("https://www.linkedin.com/sales/")
    time.sleep(3)
    if "login" in page.url or "checkpoint" in page.url:
        input("🔐 Bitte manuell einloggen und ENTER drücken...")

    with open(output_file, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=headers)
        writer.writeheader()

        for row in rows:
            firma = row.get(firma_field, "").strip()
            if not firma:
                writer.writerow(row)
                continue
            
            contacts = scrape_leads(page, firma)
            for idx, contact in enumerate(contacts[:MAX_KONTAKTE_PRO_FIRMA]):
                for k, v in contact.items():
                    row[f"{k} {idx+1}"] = v
            writer.writerow(row)
            time.sleep(random.uniform(*WARTEN_ZWISCHEN_FIRMEN))
    
    browser.close()
    p.stop()
    print(f"✅ Fertig! Ergebnisse in: {output_file}")

if __name__ == "__main__":
    main()
