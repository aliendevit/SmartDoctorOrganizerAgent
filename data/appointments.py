# data/appointments.py
import os, json, re
from datetime import datetime
from typing import List, Dict, Optional

try:
    from utils.app_paths import reports_dir
except Exception:
    def reports_dir() -> str:
        from pathlib import Path
        p = Path.home() / "Desktop" / "reports"
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

_DATE_FMTS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d")
_TIME_FMTS = ("%I:%M %p", "%H:%M")

def _parse_date(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    for f in _DATE_FMTS:
        try: return datetime.strptime(s, f)
        except Exception: pass
    return None

def _parse_time(s: str):
    s = (s or "").strip()
    for f in _TIME_FMTS:
        try: return datetime.strptime(s, f).time()
        except Exception: pass
    m = re.search(r"\b(\d{1,2}:\d{2}\s*[APMapm]{0,2})\b", s)
    if m: return _parse_time(m.group(1))
    return None

def _iter_json() -> List[Dict]:
    out, root = [], reports_dir()
    for name in os.listdir(root):
        if name.lower().endswith(".json"):
            p = os.path.join(root, name)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                    if isinstance(obj, dict):
                        obj["_path"] = p
                        out.append(obj)
            except Exception:
                pass
    return out

def appointments_on(date_obj: datetime) -> List[Dict]:
    want = date_obj.strftime("%d-%m-%Y")
    items = []
    for rec in _iter_json():
        apd = (rec.get("Appointment Date") or "").strip()
        d = _parse_date(apd)
        if not d or d.strftime("%d-%m-%Y") != want:
            continue
        t = _parse_time(rec.get("Appointment Time") or "")
        items.append({
            "Name": rec.get("Name","Unknown"),
            "Age": rec.get("Age",""),
            "Symptoms": rec.get("Symptoms", []),
            "Notes": rec.get("Notes",""),
            "Appointment Date": want,
            "Appointment Time": (t.strftime("%I:%M %p") if t else "Not Specified"),
            "_time": t,
            "_src": rec.get("_path",""),
        })
    items.sort(key=lambda r: (r["_time"] is None, r["_time"] or datetime.min.time()))
    return items
