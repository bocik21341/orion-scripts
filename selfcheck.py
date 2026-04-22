#!/usr/bin/env python3
"""
selfcheck.py — Diagnostyka stanu Oriona.

Sprawdza: email, Mastodon, dysk, RAM, uptime, pliki pamięci.
Uruchamiaj raz dziennie lub przy starcie sesji.
"""
import os, imaplib, ssl, requests, shutil, subprocess
from datetime import datetime

TOKEN     = "9w_MQV0uEgR0bQQXjkRYQSuKR5Mq4zaog9s0fJNJ_Jo"
IMAP_HOST = "s63.cyber-folks.pl"
EMAIL_USER = "bocik@jjii.pl"
EMAIL_PASS = "ome9w2i-z-LeSIW%"
MEMORY_DIR = "/root/.openclaw/workspace/memory"
OK  = "✅"
ERR = "❌"
WARN = "⚠️"

results = []

def check(name, fn):
    try:
        ok, msg = fn()
        icon = OK if ok else ERR
        results.append(f"{icon} {name}: {msg}")
    except Exception as e:
        results.append(f"{ERR} {name}: BŁĄD — {e}")

# Email IMAP
def check_email():
    ctx = ssl.create_default_context()
    m = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ctx)
    m.login(EMAIL_USER, EMAIL_PASS)
    m.select("INBOX")
    _, data = m.search(None, "UNSEEN")
    unseen = len(data[0].split())
    m.logout()
    return True, f"Połączenie OK | {unseen} nieprzeczytanych"

# Mastodon API
def check_mastodon():
    r = requests.get("https://mastodon.social/api/v1/accounts/verify_credentials",
        headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
    if r.status_code == 200:
        d = r.json()
        return True, f"@{d['username']} | {d['statuses_count']} postów | {d['followers_count']} followersów"
    return False, f"HTTP {r.status_code}"

# Dysk
def check_disk():
    usage = shutil.disk_usage("/")
    free_gb = usage.free / 1e9
    pct = usage.used / usage.total * 100
    ok = free_gb > 1.0
    return ok, f"{free_gb:.1f}GB wolne ({pct:.0f}% zajęte)"

# RAM
def check_ram():
    with open("/proc/meminfo") as f:
        lines = {l.split(':')[0]: int(l.split()[1]) for l in f if ':' in l}
    free_mb = (lines.get("MemAvailable", 0)) // 1024
    total_mb = lines.get("MemTotal", 1) // 1024
    ok = free_mb > 200
    return ok, f"{free_mb}MB wolne / {total_mb}MB total"

# Pliki pamięci
def check_memory():
    files = os.listdir(MEMORY_DIR) if os.path.exists(MEMORY_DIR) else []
    today = datetime.utcnow().strftime("%Y-%m-%d")
    has_today = f"{today}.md" in files
    has_memory = os.path.exists("/root/.openclaw/workspace/MEMORY.md")
    if has_today and has_memory:
        return True, f"{len(files)} plików | dziennik dziś: tak | MEMORY.md: tak"
    return False, f"dziennik dziś: {has_today} | MEMORY.md: {has_memory}"

# Uptime
def check_uptime():
    with open("/proc/uptime") as f:
        secs = float(f.read().split()[0])
    mins = int(secs // 60)
    return True, f"{mins} minut"

check("Email IMAP",  check_email)
check("Mastodon",    check_mastodon)
check("Dysk",        check_disk)
check("RAM",         check_ram)
check("Pliki pamięci", check_memory)
check("Uptime",      check_uptime)

print(f"\n=== Orion selfcheck — {datetime.utcnow():%Y-%m-%d %H:%M UTC} ===\n")
for r in results:
    print(r)
print()
