#!/usr/bin/env python3
"""
inbox.py — Szybki podgląd skrzynki email.

Użycie:
  python3 inbox.py              # nieprzeczytane
  python3 inbox.py --all        # wszystkie (max 10)
  python3 inbox.py --read <id>  # treść wiadomości
  python3 inbox.py --send <to> <subject> <body>
"""
import sys, imaplib, smtplib, ssl, email
from email.mime.text import MIMEText
from email.header import decode_header

HOST  = "s63.cyber-folks.pl"
USER  = "bocik@jjii.pl"
PASS  = "ome9w2i-z-LeSIW%"

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

def connect():
    ctx = ssl.create_default_context()
    m = imaplib.IMAP4_SSL(HOST, 993, ssl_context=ctx)
    m.login(USER, PASS)
    return m

def list_messages(unseen_only=True):
    m = connect()
    m.select("INBOX")
    criteria = "UNSEEN" if unseen_only else "ALL"
    _, data = m.search(None, criteria)
    ids = data[0].split()
    if not ids:
        print("Brak wiadomości." if unseen_only else "Skrzynka pusta.")
        m.logout(); return
    for mid in ids[-10:]:
        _, msg_data = m.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
        msg = email.message_from_bytes(msg_data[0][1])
        print(f"[{mid.decode()}] {decode_str(msg['Date'])[:16]} | Od: {decode_str(msg['From'])[:35]} | {decode_str(msg['Subject'])[:50]}")
    m.logout()

def read_message(msg_id: str):
    m = connect()
    m.select("INBOX")
    _, msg_data = m.fetch(msg_id.encode(), "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    print(f"Od: {decode_str(msg['From'])}")
    print(f"Temat: {decode_str(msg['Subject'])}")
    print(f"Data: {msg['Date']}")
    print("─" * 60)
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                print(part.get_payload(decode=True).decode(errors="replace")[:2000])
                break
    else:
        print(msg.get_payload(decode=True).decode(errors="replace")[:2000])
    m.logout()

def send(to: str, subject: str, body: str):
    ctx = ssl.create_default_context()
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = USER
    msg["To"] = to
    msg["Subject"] = subject
    with smtplib.SMTP_SSL(HOST, 465, context=ctx) as smtp:
        smtp.login(USER, PASS)
        smtp.sendmail(USER, [to], msg.as_string())
    print(f"✅ Wysłano do {to}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        list_messages(unseen_only=True)
    elif args[0] == "--all":
        list_messages(unseen_only=False)
    elif args[0] == "--read" and len(args) > 1:
        read_message(args[1])
    elif args[0] == "--send" and len(args) >= 4:
        send(args[1], args[2], " ".join(args[3:]))
    else:
        print(__doc__)
