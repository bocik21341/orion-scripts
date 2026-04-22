#!/usr/bin/env python3
"""
toot.py — Mastodon CLI dla Oriona.

Użycie:
  python3 toot.py post "treść"          # nowy post
  python3 toot.py reply <id> "treść"    # odpowiedź
  python3 toot.py timeline              # home timeline
  python3 toot.py notifs                # powiadomienia
  python3 toot.py delete <id>           # usuń post
"""
import sys, requests, re, json

TOKEN = "9w_MQV0uEgR0bQQXjkRYQSuKR5Mq4zaog9s0fJNJ_Jo"
BASE  = "https://mastodon.social/api/v1"
H     = {"Authorization": f"Bearer {TOKEN}"}

def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()

def cmd_post(text, reply_to=None):
    data = {"status": text, "visibility": "public"}
    if reply_to:
        data["in_reply_to_id"] = reply_to
    r = requests.post(f"{BASE}/statuses", headers=H, json=data)
    d = r.json()
    if "url" in d:
        print(f"✅ {d['url']}")
    else:
        print(f"❌ {d}")

def cmd_timeline():
    r = requests.get(f"{BASE}/timelines/home?limit=10", headers=H)
    for s in r.json():
        acct = s["account"]["acct"]
        txt  = strip_html(s["content"])[:100]
        print(f"@{acct}: {txt}")

def cmd_notifs():
    r = requests.get(f"{BASE}/notifications?limit=15", headers=H)
    for n in r.json():
        ntype = n["type"]
        acct  = n["account"]["acct"]
        status = n.get("status", {})
        txt = strip_html(status.get("content", ""))[:80] if status else ""
        nid = status.get("id", "") if status else ""
        print(f"[{ntype}] @{acct} (status_id:{nid}): {txt}")

def cmd_delete(status_id):
    r = requests.delete(f"{BASE}/statuses/{status_id}", headers=H)
    d = r.json()
    print(f"✅ Usunięto {d.get('id','?')}" if "id" in d else f"❌ {d}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit()
    cmd = args[0]
    if cmd == "post" and len(args) > 1:
        cmd_post(" ".join(args[1:]))
    elif cmd == "reply" and len(args) > 2:
        cmd_post(" ".join(args[2:]), reply_to=args[1])
    elif cmd == "timeline":
        cmd_timeline()
    elif cmd == "notifs":
        cmd_notifs()
    elif cmd == "delete" and len(args) > 1:
        cmd_delete(args[1])
    else:
        print(__doc__)
