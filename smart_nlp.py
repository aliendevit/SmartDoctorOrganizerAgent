# smart_nlp.py
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import dateparser
from rapidfuzz import fuzz, process

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except Exception as e:
    spacy = None
    PhraseMatcher = None

_SYMPTOM_LEXICON = [
    # general
    "fever","cough","headache","nausea","vomiting","diarrhea","fatigue","weakness","dizziness","shortness of breath",
    "chills","sore throat","runny nose","congestion","rash","pain","chest pain","abdominal pain","back pain",
    # dental focus (since your app targets clinics)
    "toothache","sensitivity","swelling","bleeding gums","gingival bleeding","gum pain","jaw pain","abscess",
    "loose tooth","bad breath","halitosis","ulcer","canker sore","sensitivity to cold","sensitivity to hot",
]

_AGE_PAT = re.compile(r"\b(\d{1,3})\s*(?:years?\s*old|y/?o|yrs?|yo)\b", re.I)
_AGE_LOOSE = re.compile(r"\bage\s*(?:is|:)?\s*(\d{1,3})\b", re.I)

class SmartExtractor:
    def __init__(self):
        self.nlp = None
        self.matcher = None
        if spacy is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                self.nlp = spacy.blank("en")
            if PhraseMatcher is not None:
                self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
                pats = [self.nlp.make_doc(t) for t in _SYMPTOM_LEXICON]
                self.matcher.add("SYMPTOMS", pats)

    # ---------- public ----------
    def extract(self, text: str) -> Dict:
        text = (text or "").strip()
        doc = self.nlp(text) if self.nlp else None

        name = self._extract_name(doc, text)
        age = self._extract_age(text)
        symptoms = self._extract_symptoms(doc, text)
        summary = self._make_summary(text, symptoms)
        appt_date, appt_time = self._extract_appointment(text)
        followup_date = self._extract_followup(text)

        return {
            "Name": name or "Unknown",
            "Age": age if age is not None else "",
            "Symptoms": symptoms,
            "Notes": "",
            "Date": datetime.today().strftime("%d-%m-%Y"),
            "Appointment Date": appt_date or "Not Specified",
            "Appointment Time": appt_time or "Not Specified",
            "Summary": summary,
            "Follow-Up Date": followup_date or "",
        }

    # ---------- helpers ----------
    def _extract_name(self, doc, text) -> Optional[str]:
        # Prefer spaCy PERSON
        if doc is not None:
            for ent in doc.ents:
                if ent.label_ == "PERSON" and 2 <= len(ent.text) <= 80:
                    return ent.text.strip()
        # Fallback: “Patient <Name>”
        m = re.search(r"\bPatient\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,2})\b", text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_age(self, text) -> Optional[int]:
        m = _AGE_PAT.search(text)
        if m:
            n = int(m.group(1))
            if 0 < n < 120:
                return n
        m2 = _AGE_LOOSE.search(text)
        if m2:
            n = int(m2.group(1))
            if 0 < n < 120:
                return n
        # Last resort: first 1–2 digit followed by “yo/yr”
        m3 = re.search(r"\b(\d{1,2})\b.*?(?:yo|yr|yrs)\b", text, re.I)
        if m3:
            n = int(m3.group(1))
            if 0 < n < 120:
                return n
        return None

    def _extract_symptoms(self, doc, text) -> List[str]:
        found = set()
        # Phrase matcher (robust, ML-ish via tokenization)
        if doc is not None and self.matcher is not None:
            for _, start, end in self.matcher(doc):
                s = doc[start:end].text.lower().strip()
                found.add(s)
        # Fuzzy catch for near-misses (“tooth ake”, “bleedin gums”)
        candidates = set(w.lower() for w in re.findall(r"[a-zA-Z][a-zA-Z\s\-]{2,}", text))
        for choice, score, _ in process.extract(
            " ".join(candidates),
            _SYMPTOM_LEXICON,
            scorer=fuzz.token_set_ratio,
            limit=20,
        ):
            if score >= 85:
                found.add(choice.lower())
        # Deduplicate & sort by appearance
        ordered = []
        for term in _SYMPTOM_LEXICON:
            if term in found:
                ordered.append(term)
        # Add any extras detected first time
        for t in sorted(found):
            if t not in ordered:
                ordered.append(t)
        return ordered[:10]

    def _make_summary(self, text, symptoms) -> str:
        # First sentence + top symptoms
        first = re.split(r'(?<=[.!?])\s+', text.strip())
        first_sent = first[0] if first else ""
        sym = ", ".join(symptoms[:4])
        bits = []
        if first_sent:
            bits.append(first_sent)
        if sym:
            bits.append(f"Key symptoms: {sym}.")
        return " ".join(bits).strip() or text[:160]

    def _extract_appointment(self, text) -> (Optional[str], Optional[str]):
        # Look for explicit “appointment … <date/time>”
        date_res = dateparser.search.search_dates(
            text, settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.now()}
        )
        if not date_res:
            return None, None

        # Prefer phrases near “appointment”, “appt”, “visit”, “see you”
        def boost(dctx: str) -> int:
            ctx = dctx.lower()
            hints = ["appointment", "appt", "visit", "see you", "schedule", "scheduled"]
            return sum(1 for h in hints if h in ctx)

        best = max(
            date_res,
            key=lambda kv: (boost(text[max(0, kv[1].start()-25): kv[1].end()+25]), kv[1].end()-kv[1].start())
        )
        dt = best[1]
        date_str = dt.strftime("%d-%m-%Y")
        time_str = dt.strftime("%I:%M %p").lstrip("0")
        return date_str, time_str

    def _extract_followup(self, text) -> Optional[str]:
        # Common patterns: "follow up in 2 weeks", "FU in 10 days", "review next month"
        m = re.search(r"\b(f/u|follow[- ]?up|review)\b.*?\b(in|after)\s+(\d{1,3})\s+(day|days|week|weeks|month|months)\b", text, re.I)
        if m:
            amt = int(m.group(3))
            unit = m.group(4).lower()
            delta = {"day": "days", "days": "days", "week": "weeks", "weeks": "weeks", "month": "days", "months": "days"}[unit]
            # months ~= 30 days
            days = amt * (1 if "day" in unit else 7 if "week" in unit else 30)
            when = datetime.today() + timedelta(days=days)
            return when.strftime("%d-%m-%Y")

        # Try dateparser around the phrase “follow up”
        snippet = None
        mm = re.search(r"(?:follow[- ]?up|f/u|review).{0,60}", text, re.I)
        if mm:
            snippet = mm.group(0)
        if snippet:
            dt = dateparser.parse(snippet, settings={"PREFER_DATES_FROM": "future"})
            if isinstance(dt, datetime):
                return dt.strftime("%d-%m-%Y")
        return None
