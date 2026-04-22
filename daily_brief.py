#!/usr/bin/env python3
"""
daily_brief.py — Poranny brief dla usera.
Sprawdza: email, Mastodon powiadomienia, ceny, wysyła podsumowanie mailem.
"""
import imaplib, smtplib, ssl, email, requests, json, os, re
from email.mime.text import MIMEText
from email.header import decode_header
from datetime import datetime

HOST       = "s63.cyber-folks.pl"
EMAIL_USER = "bocik@jjii.pl"
EMAIL_PASS = "ome9w2i-z-LeSIW%"
MASTO_TOKEN = "9w_MQV0uEgR0bQQXjkRYQSuKR5Mq4zaog9s0fJNJ_Jo"
PRICE_DB   = "/root/.openclaw/workspace/memory/price_monitor.json"

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result

sections = []

# ── Email ────────────────────────────────────────────────────────────────────
try:
    ctx = ssl.create_default_context()
    m = imaplib.IMAP4_SSL(HOST, 993, ssl_context=ctx)
    m.login(EMAIL_USER, EMAIL_PASS)
    m.select("INBOX")
    _, data = m.search(None, "UNSEEN")
    ids = data[0].split()
    if ids:
        lines = [f"📧 Nowe maile ({len(ids)}):"]
        for mid in ids[-5:]:
            _, md = m.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT)])")
            msg = email.message_from_bytes(md[0][1])
            lines.append(f"  Od: {decode_str(msg['From'])[:40]} | {decode_str(msg['Subject'])[:50]}")
        sections.append("\n".join(lines))
    else:
        sections.append("📧 Email: brak nowych wiadomości")
    m.logout()
except Exception as e:
    sections.append(f"📧 Email: błąd — {e}")

# ── Mastodon ─────────────────────────────────────────────────────────────────
try:
    headers = {"Authorization": f"Bearer {MASTO_TOKEN}"}
    r = requests.get("https://mastodon.social/api/v1/notifications?limit=10", 
                     headers=headers, timeout=10)
    notifs = r.json()
    mentions = [n for n in notifs if n.get("type") == "mention"]
    reblogs  = [n for n in notifs if n.get("type") == "reblog"]
    follows  = [n for n in notifs if n.get("type") == "follow"]
    
    lines = [f"🐘 Mastodon: {len(notifs)} powiadomień"]
    if mentions:
        lines.append(f"  Mentions: {len(mentions)}")
        for n in mentions[:3]:
            acct = n["account"]["acct"]
            txt = re.sub('<[^>]+>', '', n.get("status", {}).get("content", ""))[:80]
            lines.append(f"    @{acct}: {txt}")
    if reblogs:
        lines.append(f"  Reblogi: {len(reblogs)}")
    if follows:
        lines.append(f"  Nowi followersi: {len(follows)}")
    sections.append("\n".join(lines))
except Exception as e:
    sections.append(f"🐘 Mastodon: błąd — {e}")

# ── Ceny ─────────────────────────────────────────────────────────────────────
try:
    if os.path.exists(PRICE_DB):
        with open(PRICE_DB) as f:
            db = json.load(f)
        products = db.get("products", [])
        if products:
            lines = [f"💰 Monitor cen ({len(products)} produktów):"]
            for p in products:
                alert = p.get("alert_price")
                price = p.get("last_price")
                status = " 🚨 ALERT!" if (alert and price and price <= alert) else ""
                lines.append(f"  {p['name'][:40]}: {price} PLN{status}")
            sections.append("\n".join(lines))
except Exception as e:
    sections.append(f"💰 Ceny: błąd — {e}")

# ── Wyślij brief ─────────────────────────────────────────────────────────────
now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
body = f"Orion — Poranny brief\n{now}\n\n"
body += "\n\n".join(sections)
body += "\n\n---\norion_kiloclaw@mastodon.social"

print(body)

ctx = ssl.create_default_context()
msg = MIMEText(body, "plain", "utf-8")
msg["From"] = EMAIL_USER
msg["To"]   = EMAIL_USER
msg["Subject"] = f"☀️ Brief — {datetime.utcnow().strftime('%d.%m.%Y')}"
with smtplib.SMTP_SSL(HOST, 465, context=ctx) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.sendmail(EMAIL_USER, [EMAIL_USER], msg.as_string())
print("\n✅ Brief wysłany na email.")
