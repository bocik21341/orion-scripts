#!/usr/bin/env python3
"""
fetch.py — Inteligentny fetcher stron internetowych.

Próbuje kolejno: curl → chromium headless
Zwraca czysty tekst lub HTML.

Użycie:
  python3 fetch.py <url> [--text] [--price]
"""
import sys, subprocess, re

def fetch_curl(url: str) -> str | None:
    result = subprocess.run([
        "curl", "-sL", url,
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-H", "Accept-Language: pl-PL,pl;q=0.9,en;q=0.8",
        "--compressed", "--max-time", "10"
    ], capture_output=True, text=True, timeout=15)
    html = result.stdout
    if "Just a moment" in html or "Enable JavaScript" in html or len(html) < 500:
        return None
    return html

def fetch_chromium(url: str) -> str | None:
    result = subprocess.run([
        "chromium", "--headless=new", "--no-sandbox",
        "--dump-dom", "--virtual-time-budget=8000", url
    ], capture_output=True, text=True, timeout=35)
    return result.stdout if result.stdout else None

def fetch(url: str) -> str:
    html = fetch_curl(url)
    if not html:
        html = fetch_chromium(url)
    return html or ""

def to_text(html: str) -> str:
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_price(html: str) -> dict | None:
    import json
    ld_blocks = re.findall(r'type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for block in ld_blocks:
        try:
            d = json.loads(block)
            if "offers" in d:
                offers = d["offers"]
                return {
                    "name": d.get("name", "?"),
                    "price": offers.get("price"),
                    "currency": offers.get("priceCurrency", "PLN"),
                    "in_stock": "InStock" in offers.get("availability", ""),
                }
        except: pass
    prices = re.findall(r'"price"\s*:\s*(\d+(?:\.\d+)?)', html)
    return {"price": prices[0]} if prices else None

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    url = args[0]
    html = fetch(url)
    if "--price" in args:
        info = extract_price(html)
        print(info or "Brak ceny")
    elif "--text" in args:
        print(to_text(html)[:3000])
    else:
        print(html[:5000])
