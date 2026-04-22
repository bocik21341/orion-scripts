#!/usr/bin/env python3
"""
mastodon_notify.py — Sprawdza powiadomienia Mastodon i wysyła email z podsumowaniem.
Uruchamiaj np. co godzinę przez heartbeat lub cron.
"""
import requests, json, os, imaplib, smtplib, ssl
from email.mime.text import MIMEText
from datetime import datetime

TOKEN = "9w_MQV0uEgR0bQQXjkRYQSuKR5Mq4zaog9s0fJNJ_Jo"
EMAIL_USER = "bocik@jjii.pl"
EMAIL_PASS = "ome9w2i-z-LeSIW%"
SMTP_HOST  = "s63.cyber-folks.pl"
STATE_FILE = "/root/.openclaw/workspace/memory/mastodon_last_notif.txt"

def get_last_id():
    if os.path.exists(STATE_FILE):
        return open(STATE_FILE).read().strip()
    return None

def save_last_id(nid):
    with open(STATE_FILE, "w") as f:
        f.write(str(nid))

def check_notifications():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"limit": 20}
    last_id = get_last_id()
    if last_id:
        params["since_id"] = last_id

    r = requests.get("https://mastodon.social/api/v1/notifications", 
                     headers=headers, params=params)
    notifs = r.json()
    if not notifs:
        print("Brak nowych powiadomień.")
        return

    import re
    lines = []
    for n in notifs:
        ntype = n.get("type")
        acct  = n.get("account", {}).get("acct", "?")
        status = n.get("status", {})
        content = re.sub("<[^>]+>", "", status.get("content", "")) if status else ""
        lines.append(f"[{ntype}] @{acct}: {content[:120]}")

    save_last_id(notifs[0]["id"])

    body = f"Orion — Mastodon\n{datetime.utcnow():%Y-%m-%d %H:%M UTC}\n\n"
    body += "\n".join(lines)
    print(body)

    # Wyślij email tylko jeśli są mentions/replies
    important = [n for n in notifs if n.get("type") in ("mention", "reply")]
    if important:
        ctx = ssl.create_default_context()
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = EMAIL_USER
        msg["To"]   = EMAIL_USER
        msg["Subject"] = f"🐘 Mastodon: {len(important)} nowych wiadomości"
        with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ctx) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
        print(f"Email wysłany ({len(important)} ważnych powiadomień).")

if __name__ == "__main__":
    check_notifications()
