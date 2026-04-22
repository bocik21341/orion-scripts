#!/usr/bin/env python3
"""
rss.py — Lokalny RSS reader Oriona.

Użycie:
  python3 rss.py                  # pokaż nowe wpisy
  python3 rss.py --all            # wszystkie (bez filtra "nowe")
  python3 rss.py --add <url>      # dodaj feed
  python3 rss.py --list           # lista feedów
"""
import feedparser, json, os, sys, hashlib
from datetime import datetime

DB_FILE    = "/root/.openclaw/workspace/memory/rss_state.json"
SEEN_FILE  = "/root/.openclaw/workspace/memory/rss_seen.json"

DEFAULT_FEEDS = [
    {"name": "Hacker News",         "url": "https://news.ycombinator.com/rss"},
    {"name": "Lobsters",            "url": "https://lobste.rs/rss"},
    {"name": "Simon Willison",      "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Drew DeVault",        "url": "https://drewdevault.com/blog/index.xml"},
    {"name": "Mastodon AI tag",     "url": "https://mastodon.social/tags/ai.rss"},
]

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {"feeds": DEFAULT_FEEDS}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def entry_id(entry):
    return hashlib.md5((entry.get("link","") + entry.get("title","")).encode()).hexdigest()

def fetch_feed(feed: dict, seen: set, show_all=False):
    try:
        d = feedparser.parse(feed["url"])
        items = []
        for e in d.entries[:10]:
            eid = entry_id(e)
            if not show_all and eid in seen:
                continue
            items.append({
                "id":      eid,
                "title":   e.get("title", "?")[:100],
                "link":    e.get("link", ""),
                "summary": e.get("summary", "")[:200],
            })
        return items
    except Exception as ex:
        return []

def cmd_show(show_all=False):
    db = load_db()
    seen = load_seen()
    new_seen = set(seen)
    total = 0

    for feed in db["feeds"]:
        items = fetch_feed(feed, seen, show_all)
        if not items:
            continue
        print(f"\n── {feed['name']} {'(wszystkie)' if show_all else f'({len(items)} nowych)'}")
        for item in items[:5]:
            print(f"  • {item['title']}")
            print(f"    {item['link']}")
            new_seen.add(item["id"])
            total += 1

    save_seen(new_seen)
    if total == 0:
        print("Brak nowych wpisów.")
    else:
        print(f"\nŁącznie: {total} wpisów")

def cmd_add(url: str):
    db = load_db()
    d = feedparser.parse(url)
    name = d.feed.get("title", url)[:50]
    db["feeds"].append({"name": name, "url": url})
    save_db(db)
    print(f"✅ Dodano: {name}")

def cmd_list():
    db = load_db()
    for i, f in enumerate(db["feeds"], 1):
        print(f"{i:2}. {f['name'][:40]:<40} {f['url']}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--list" in args:
        cmd_list()
    elif "--add" in args:
        idx = args.index("--add")
        cmd_add(args[idx+1])
    elif "--all" in args:
        cmd_show(show_all=True)
    else:
        cmd_show(show_all=False)
