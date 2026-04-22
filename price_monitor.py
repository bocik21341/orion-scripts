#!/usr/bin/env python3
"""
price_monitor.py — Monitor cen produktów x-kom.pl

Użycie:
  python3 price_monitor.py add <url> [--alert <cena>]
  python3 price_monitor.py check
  python3 price_monitor.py list

Przykład:
  python3 price_monitor.py add "https://www.x-kom.pl/p/1510054-..." --alert 49
  python3 price_monitor.py check
"""

import json, os, sys, subprocess, re, smtplib, ssl, time
from email.mime.text import MIMEText
from datetime import datetime

DB_FILE = "/root/.openclaw/workspace/memory/price_monitor.json"
EMAIL_FROM = "bocik@jjii.pl"
EMAIL_TO   = "bocik@jjii.pl"
SMTP_HOST  = "s63.cyber-folks.pl"
SMTP_PASS  = "ome9w2i-z-LeSIW%"


def load_db():
    if not os.path.exists(DB_FILE):
        return {"products": []}
    with open(DB_FILE) as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def fetch_price(url: str) -> dict:
    """Pobierz cenę przez chromium headless."""
    result = subprocess.run([
        "chromium", "--headless=new", "--no-sandbox",
        "--dump-dom", "--virtual-time-budget=8000", url
    ], capture_output=True, text=True, timeout=30)
    html = result.stdout

    # Szukaj JSON-LD z ceną
    ld_blocks = re.findall(r'type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for block in ld_blocks:
        try:
            d = json.loads(block)
            if "offers" in d:
                offers = d["offers"]
                price = offers.get("price")
                currency = offers.get("priceCurrency", "PLN")
                availability = "InStock" in offers.get("availability", "")
                name = d.get("name", "?")
                return {
                    "name": name,
                    "price": float(price) if price else None,
                    "currency": currency,
                    "in_stock": availability,
                    "url": url,
                    "checked_at": datetime.utcnow().isoformat()
                }
        except:
            pass

    # Fallback: regex
    prices = re.findall(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    if prices:
        return {
            "name": "?",
            "price": float(prices[0]),
            "currency": "PLN",
            "in_stock": True,
            "url": url,
            "checked_at": datetime.utcnow().isoformat()
        }
    return {"name": "?", "price": None, "url": url, "checked_at": datetime.utcnow().isoformat()}


def send_email(subject: str, body: str):
    ctx = ssl.create_default_context()
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx) as smtp:
        smtp.login(EMAIL_FROM, SMTP_PASS)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())


def cmd_add(url: str, alert_price: float = None, name: str = None):
    db = load_db()
    # Sprawdź czy już jest
    for p in db["products"]:
        if p["url"] == url:
            print(f"Produkt już jest na liście: {p.get('name', url)}")
            return

    print(f"Dodaję i sprawdzam cenę: {url}")
    info = fetch_price(url)
    entry = {
        "url": url,
        "name": name or info.get("name", "?"),
        "alert_price": alert_price,
        "last_price": info.get("price"),
        "last_checked": info.get("checked_at"),
        "history": [{"price": info.get("price"), "ts": info.get("checked_at")}]
    }
    db["products"].append(entry)
    save_db(db)
    print(f"✅ Dodano: {entry['name']} — {info.get('price')} {info.get('currency', 'PLN')}")
    if alert_price:
        print(f"   Alert gdy cena ≤ {alert_price} PLN")


def cmd_check():
    db = load_db()
    if not db["products"]:
        print("Brak produktów na liście.")
        return

    alerts = []
    for p in db["products"]:
        print(f"Sprawdzam: {p['name']} ...")
        info = fetch_price(p["url"])
        new_price = info.get("price")
        old_price = p.get("last_price")

        p["last_price"] = new_price
        p["last_checked"] = info.get("checked_at")
        if "name" in info and info["name"] != "?":
            p["name"] = info["name"]
        p.setdefault("history", []).append({"price": new_price, "ts": info.get("checked_at")})

        change = ""
        if old_price and new_price:
            diff = new_price - old_price
            if diff < 0:
                change = f" ⬇️ TANIEJ o {abs(diff):.0f} zł!"
            elif diff > 0:
                change = f" ⬆️ drożej o {diff:.0f} zł"

        print(f"  {p['name']}: {new_price} PLN{change}")

        # Alert email
        if p.get("alert_price") and new_price and new_price <= p["alert_price"]:
            alerts.append(p)
            print(f"  🚨 ALERT! Cena {new_price} ≤ {p['alert_price']} PLN")

    save_db(db)

    if alerts:
        body = "Orion — monitor cen\n\nALERTY CENOWE:\n\n"
        for p in alerts:
            body += f"• {p['name']}\n  Cena: {p['last_price']} PLN (alert: ≤{p['alert_price']})\n  {p['url']}\n\n"
        send_email("🚨 Alert cenowy — x-kom.pl", body)
        print(f"\nWysłano email z {len(alerts)} alertami.")


def cmd_list():
    db = load_db()
    if not db["products"]:
        print("Lista jest pusta.")
        return
    print(f"\n{'Produkt':<40} {'Cena':>10} {'Alert':>10} {'Sprawdzono'}")
    print("-" * 80)
    for p in db["products"]:
        alert = f"≤{p['alert_price']}" if p.get("alert_price") else "-"
        checked = p.get("last_checked", "?")[:16] if p.get("last_checked") else "?"
        print(f"{p['name'][:39]:<40} {str(p.get('last_price','?'))+' PLN':>10} {alert:>10}  {checked}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "check":
        cmd_check()
    elif args[0] == "add" and len(args) >= 2:
        url = args[1]
        alert = None
        if "--alert" in args:
            idx = args.index("--alert")
            alert = float(args[idx+1])
        cmd_add(url, alert)
    else:
        print(__doc__)
