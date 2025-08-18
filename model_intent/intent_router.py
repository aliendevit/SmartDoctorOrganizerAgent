# model_intent/intent_router.py
import re, datetime
from typing import Dict
from dateparser.search import search_dates

def _titlecase(name: str) -> str:
    return " ".join(w.capitalize() for w in name.split())

def _guess_intent(t: str) -> str:
    tl = t.lower()
    if re.search(r"\b(appoint|schedule|book|see\s+(?:dr|doctor))", tl):
        return "book_appointment"
    if re.search(r"\b(pay|paid|payment|deposit|balance|invoice|receipt|amount)\b", tl):
        return "update_payment"
    if re.search(r"\b(report|summary|note|letter|prescription)\b", tl):
        return "create_report"
    return "small_talk"

def _find_name(t: str) -> str:
    tl = t.lower()

    # explicit phrasing: "person name muhammad", "name is muhammad", "for muhammad"
    pats = [
        r"\b(?:person\s+name|patient\s+name|client\s+name|name\s+is)\s+(?P<n>[a-z][\w'\-]*(?:\s+[a-z][\w'\-]*){0,3})",
        r"\bfor\s+(?P<n>[a-z][\w'\-]*(?:\s+[a-z][\w'\-]*){0,3})",
    ]
    for p in pats:
        m = re.search(p, tl, flags=re.I)
        if m:
            return _titlecase(m.group("n").strip())
    return ""

def _find_amount(t: str) -> str:
    tl = t.lower()
    if not re.search(r"\b(pay|paid|payment|deposit|balance|invoice|amount)\b", tl):
        return ""
    m = re.search(r"\$?\s*(\d{1,3}(?:[,\d]{3})*(?:\.\d+)?)", tl)
    return m.group(1) if m else ""

def _find_datetime(t: str) -> Dict[str, str]:
    """
    Use search_dates with 'future' preference.
    Returns dict with optional 'date' (dd-MM-yyyy) and 'time' (hh:mm AM/PM).
    """
    settings = {
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": datetime.datetime.now(),
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    found = search_dates(t, settings=settings)
    if not found:
        return {}

    dt = found[0][1]
    out = {"date": dt.strftime("%d-%m-%Y")}
    # only set time if the user actually said one
    if re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", t, flags=re.I):
        out["time"] = dt.strftime("%I:%M %p")
    return out

def route(text: str) -> Dict[str, str]:
    """
    Returns slots: intent, name?, date?, time?, amount?
    """
    slots: Dict[str, str] = {"intent": _guess_intent(text)}
    name = _find_name(text)
    if name:
        slots["name"] = name

    slots.update(_find_datetime(text))

    amt = _find_amount(text)
    if amt:
        slots["amount"] = amt

    return slots
