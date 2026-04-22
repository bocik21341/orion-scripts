#!/usr/bin/env python3
"""
memory_maintenance.py — Utrzymanie pamięci Oriona.

- Rotuje stare dzienniki (>30 dni)
- Czyści /tmp ze starych plików
- Raportuje stan workspace
"""
import os, shutil
from datetime import datetime, timedelta

MEMORY_DIR = "/root/.openclaw/workspace/memory"
WORKSPACE  = "/root/.openclaw/workspace"

now = datetime.utcnow()
report = []

# ── Rotacja starych dzienników ───────────────────────────────────────────────
removed = []
kept = []
if os.path.exists(MEMORY_DIR):
    for fname in os.listdir(MEMORY_DIR):
        if not fname.endswith(".md"):
            continue
        # Czy to plik z datą np. 2026-04-22.md?
        try:
            date = datetime.strptime(fname.replace(".md", ""), "%Y-%m-%d")
            age = (now - date).days
            if age > 30:
                os.remove(os.path.join(MEMORY_DIR, fname))
                removed.append(fname)
            else:
                kept.append(fname)
        except ValueError:
            pass  # nie jest plikiem z datą, pomijamy

if removed:
    report.append(f"🗑️  Usunięto stare dzienniki ({len(removed)}): {', '.join(removed)}")
else:
    report.append(f"📁 Dzienniki OK — {len(kept)} plików, żaden nie starszy niż 30 dni")

# ── Czyszczenie /tmp ──────────────────────────────────────────────────────────
tmp_cleaned = 0
for fname in os.listdir("/tmp"):
    fpath = os.path.join("/tmp", fname)
    try:
        stat = os.stat(fpath)
        age_hours = (now.timestamp() - stat.st_mtime) / 3600
        # Usuń pliki starsze niż 24h które wyglądają jak nasze skrypty
        if age_hours > 24 and fname.endswith((".py", ".html", ".json", ".txt")):
            os.remove(fpath)
            tmp_cleaned += 1
    except:
        pass
report.append(f"🧹 /tmp: wyczyszczono {tmp_cleaned} starych plików")

# ── Stan workspace ────────────────────────────────────────────────────────────
total_size = 0
file_count = 0
for dirpath, _, files in os.walk(WORKSPACE):
    for f in files:
        try:
            total_size += os.path.getsize(os.path.join(dirpath, f))
            file_count += 1
        except:
            pass
report.append(f"💾 Workspace: {file_count} plików, {total_size/1024:.0f} KB")

# ── Wynik ────────────────────────────────────────────────────────────────────
print(f"\n=== Memory maintenance — {now:%Y-%m-%d %H:%M UTC} ===\n")
for line in report:
    print(line)
print()
