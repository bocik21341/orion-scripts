"""
captcha_helper.py — Moduł obsługi CAPTCHA dla Oriona

Jak działa:
1. Funkcja `check(response, url)` analizuje odpowiedź HTTP
2. Jeśli wykryje CAPTCHA — zapisuje stan do pliku i rzuca CaptchaRequired
3. Caller łapie wyjątek i wywołuje `notify_user()` który wysyła mi wiadomość do czatu
4. Użytkownik rozwiązuje CAPTCHA i podaje mi token/potwierdzenie
5. `resume(solution)` ładuje stan i kontynuuje z rozwiązaniem
"""

import json, os, time, re
from dataclasses import dataclass, asdict
from typing import Optional

STATE_FILE = "/root/.openclaw/workspace/memory/captcha_state.json"

# ─── Typy CAPTCHA ────────────────────────────────────────────────────────────

CAPTCHA_TYPES = {
    "hcaptcha":    "hCaptcha (kliknij obrazki)",
    "recaptcha":   "reCAPTCHA v2 (kliknij obrazki / jestem robotem)",
    "recaptcha_v3":"reCAPTCHA v3 (niewidoczna, może wymagać reload)",
    "turnstile":   "Cloudflare Turnstile (spinner / kliknięcie)",
    "slider":      "Slider/Puzzle (przesuń element)",
    "image_text":  "Obrazek z tekstem do przepisania",
    "email_link":  "Link weryfikacyjny na email",
    "unknown":     "Nieznany typ CAPTCHA",
}

# ─── Detekcja ─────────────────────────────────────────────────────────────────

def detect(html: str, url: str = "") -> Optional[str]:
    """Analizuje HTML i zwraca typ CAPTCHA lub None jeśli brak."""
    h = html.lower()
    
    if "hcaptcha.com" in h or "h-captcha" in h:
        return "hcaptcha"
    if "recaptcha/api2" in h or "recaptcha/enterprise" in h:
        return "recaptcha"
    if "recaptcha.net" in h or "g-recaptcha" in h:
        return "recaptcha"
    if "challenges.cloudflare.com" in h or "cf-turnstile" in h or "turnstile" in h:
        return "turnstile"
    if any(x in h for x in ["slide", "slider", "puzzle", "drag"]) and "captcha" in h:
        return "slider"
    if "captcha" in h and any(x in h for x in ["<img", "image", "solve"]):
        return "image_text"
    if "confirmation_token" in url or ("confirm" in h and "email" in h):
        return "email_link"
    if "captcha" in h or "challenge" in h:
        return "unknown"
    return None


def detect_from_response(status_code: int, html: str, url: str = "") -> Optional[str]:
    """Sprawdza kod HTTP + treść. 403/429/503 często = CAPTCHA."""
    if status_code in (403, 429, 503):
        captcha_type = detect(html, url)
        if captcha_type:
            return captcha_type
        # Cloudflare challenge page bez słowa captcha
        if "cloudflare" in html.lower() and "ray id" in html.lower():
            return "turnstile"
    return detect(html, url)


# ─── Wyjątek ─────────────────────────────────────────────────────────────────

class CaptchaRequired(Exception):
    def __init__(self, captcha_type: str, url: str, task: str, extra: dict = None):
        self.captcha_type = captcha_type
        self.url = url
        self.task = task          # opis co próbowałem zrobić
        self.extra = extra or {}
        super().__init__(f"CAPTCHA required: {captcha_type} @ {url}")


# ─── Zapis/odczyt stanu ──────────────────────────────────────────────────────

def save_state(captcha_type: str, url: str, task: str, form_data: dict = None, extra: dict = None):
    state = {
        "captcha_type": captcha_type,
        "type_desc": CAPTCHA_TYPES.get(captcha_type, "?"),
        "url": url,
        "task": task,
        "form_data": form_data or {},
        "extra": extra or {},
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "solved": False,
        "solution": None,
    }
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    return state


def load_state() -> Optional[dict]:
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return json.load(f)


def mark_solved(solution: str):
    state = load_state()
    if state:
        state["solved"] = True
        state["solution"] = solution
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    return state


def clear_state():
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)


# ─── Generowanie wiadomości dla użytkownika ──────────────────────────────────

def build_user_message(state: dict) -> str:
    t = state["captcha_type"]
    url = state["url"]
    task = state["task"]
    desc = state["type_desc"]
    
    msg = f"🔒 **CAPTCHA wymagana!**\n\n"
    msg += f"Próbowałem: _{task}_\n"
    msg += f"Typ: **{desc}**\n"
    msg += f"URL: {url}\n\n"

    if t == "email_link":
        msg += "**Co zrobić:**\n"
        msg += f"1. Otwórz link: {url}\n"
        msg += "2. Rozwiąż CAPTCHA na stronie\n"
        msg += "3. Odpisz mi: `captcha: gotowe`\n"

    elif t in ("hcaptcha", "recaptcha", "turnstile"):
        msg += "**Co zrobić:**\n"
        msg += f"1. Otwórz w przeglądarce: {url}\n"
        msg += "2. Rozwiąż CAPTCHA\n"
        msg += "3. W DevTools (F12 → Network) znajdź request submit formularza\n"
        msg += "4. Skopiuj wartość pola `h-captcha-response` lub `g-recaptcha-response` lub `cf-turnstile-response`\n"
        msg += "5. Odpisz mi: `captcha: <token>`\n"

    elif t == "slider":
        msg += "**Co zrobić:**\n"
        msg += f"1. Otwórz w przeglądarce: {url}\n"
        msg += "2. Przesuń puzzle/slider\n"
        msg += "3. Jeśli się uda — skopiuj ciasteczka sesji z DevTools (Application → Cookies)\n"
        msg += "4. Odpisz mi: `captcha: gotowe` lub wklej cookies\n"

    elif t == "image_text":
        msg += "**Co zrobić:**\n"
        msg += f"1. Otwórz: {url}\n"
        msg += "2. Przepisz tekst z obrazka\n"
        msg += "3. Odpisz mi: `captcha: <tekst>`\n"

    else:
        msg += "**Co zrobić:**\n"
        msg += f"1. Otwórz: {url}\n"
        msg += "2. Rozwiąż CAPTCHA\n"
        msg += "3. Odpisz mi: `captcha: gotowe` lub wklej token\n"

    return msg


# ─── Główna funkcja sprawdzająca ─────────────────────────────────────────────

def check_and_raise(status_code: int, html: str, url: str, task: str, form_data: dict = None):
    """
    Wywołaj po każdym HTTP request.
    Jeśli CAPTCHA → zapisuje stan i rzuca CaptchaRequired.
    
    Przykład użycia:
        r = requests.post(url, data=form_data)
        captcha_helper.check_and_raise(r.status_code, r.text, url, "Rejestracja na Mastodon")
    """
    captcha_type = detect_from_response(status_code, html, url)
    if captcha_type:
        state = save_state(captcha_type, url, task, form_data)
        raise CaptchaRequired(captcha_type, url, task)
    return None  # brak CAPTCHA, wszystko OK


# ─── Parsowanie odpowiedzi użytkownika ───────────────────────────────────────

def parse_user_reply(text: str) -> Optional[str]:
    """
    Wykrywa czy wiadomość użytkownika to odpowiedź na CAPTCHA.
    Formaty: 'captcha: gotowe', 'captcha: <token>', etc.
    Zwraca rozwiązanie lub None.
    """
    text = text.strip()
    match = re.match(r'captcha\s*:\s*(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None
