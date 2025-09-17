# smart_nlp.py
# imports (top)
try:
    from dateparser.search import search_dates
except Exception:
    search_dates = None


import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import dateparser
from rapidfuzz import fuzz, process
# nlp/smart_nlp.py
from typing import Dict
from .local_gemma_it import extract_fields

class SmartExtractor:
    def extract(self, text: str) -> Dict:
        return extract_fields(text or "")

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

    def _extract_appointment(self, text: str):
        t = text or ""
        appt_date, appt_time = "", ""

        # --- dates via dateparser (robust across versions)
        date_cands = []
        if search_dates:
            try:
                for matched, dt in (search_dates(t) or []):
                    start = t.lower().find(matched.lower())
                    if start >= 0:
                        date_cands.append((start, matched, dt))
            except Exception:
                pass

        # fallback: simple regex if dateparser missing
        if not date_cands:
            for m in re.finditer(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", t):
                date_cands.append((m.start(), m.group(0), None))

        # pick the date closest to the word "appointment"
        if date_cands:
            anchor = t.lower().find("appointment")
            if anchor == -1:
                anchor = len(t) // 2
            appt_date = min(date_cands, key=lambda x: abs(x[0] - anchor))[1]

        # --- time via regex (stable)
        m = re.search(r"\b(\d{1,2}:\d{2}\s*[ap]m|\d{1,2}\s*[ap]m)\b", t, re.I)
        if m:
            appt_time = m.group(1)

        return appt_date, appt_time

    def _extract_followup(self, text: str):
        t = text or ""
        follow = ""
        date_cands = []
        if search_dates:
            try:
                for matched, dt in (search_dates(t) or []):
                    start = t.lower().find(matched.lower())
                    if start >= 0:
                        date_cands.append((start, matched, dt))
            except Exception:
                pass
        if not date_cands:
            for m in re.finditer(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", t):
                date_cands.append((m.start(), m.group(0), None))

        if date_cands:
            anchor = max(
                (t.lower().rfind("follow-up"), t.lower().rfind("follow up"), t.lower().rfind("fu")),
                default=-1
            )
            if anchor == -1:
                anchor = len(t) // 2
            follow = min(date_cands, key=lambda x: abs(x[0] - anchor))[1]
        return follow

