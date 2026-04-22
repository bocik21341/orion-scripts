#!/usr/bin/env python3
"""
remember.py — Szybkie notatki do dziennika sesji.

Użycie:
  python3 remember.py "coś ważnego"
  python3 remember.py --today        # pokaż dzisiejsze notatki
  python3 remember.py --list         # lista plików
"""
import sys, os
from datetime import datetime

MEMORY_DIR = "/root/.openclaw/workspace/memory"

def today_file():
    date = datetime.utcnow().strftime("%Y-%m-%d")
    return os.path.join(MEMORY_DIR, f"{date}.md")

def add_note(text: str):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%H:%M UTC")
    path = today_file()
    with open(path, "a") as f:
        f.write(f"\n- [{ts}] {text}\n")
    print(f"✅ Zapisano w {os.path.basename(path)}")

def show_today():
    path = today_file()
    if os.path.exists(path):
        print(open(path).read())
    else:
        print("Brak notatek na dziś.")

def list_files():
    files = sorted(os.listdir(MEMORY_DIR))
    for f in files:
        print(f)

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--today":
        show_today()
    elif args[0] == "--list":
        list_files()
    else:
        add_note(" ".join(args))
