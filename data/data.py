# data/data.py
# Unified JSON storage for clients & appointments.
# Used by: AccountsTab, DashboardTab, ClientStatsTab, AppointmentTab, ExtractionTab, etc.

import os, json
from typing import List, Dict, Tuple

# ---------- Paths ----------
_BASE = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.normpath(os.path.join(_BASE, "..", "json"))
os.makedirs(JSON_DIR, exist_ok=True)

CLIENTS_FILE = os.path.join(JSON_DIR, "clients.json")
APPOINTMENTS_FILE = os.path.join(JSON_DIR, "appointments.json")

# ---------- Helpers ----------
def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_json(path: str, data) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

def _norm_name(name: str) -> str:
    return (name or "").strip().lower()

# ---------- Clients ----------
def load_all_clients() -> List[Dict]:
    """Return the full clients list."""
    items = _read_json(CLIENTS_FILE)
    return items if isinstance(items, list) else []

def save_all_clients(items: List[Dict]) -> bool:
    """Overwrite all clients."""
    return _write_json(CLIENTS_FILE, list(items or []))

def _compute_money_fields(rec: Dict) -> Dict:
    """Ensure numeric money fields are consistent."""
    try:
        tp = float(rec.get("Total Paid", 0) or 0)
    except Exception:
        tp = 0.0
    try:
        ta = float(rec.get("Total Amount", 0) or 0)
    except Exception:
        ta = 0.0
    rec["Total Paid"] = tp
    rec["Total Amount"] = ta
    rec["Owed"] = max(0.0, ta - tp)
    return rec

def insert_client(rec: Dict) -> bool:
    """
    Upsert a client by Name. If Name missing, store as 'Unknown (N)'.
    Returns True on success.
    """
    items = load_all_clients()
    name = (rec.get("Name") or "").strip()
    if not name:
        name = f"Unknown ({len(items)+1})"
        rec["Name"] = name

    rec = _compute_money_fields(dict(rec))
    key = _norm_name(name)

    for i, it in enumerate(items):
        if _norm_name(it.get("Name")) == key:
            items[i] = {**it, **rec}
            break
    else:
        items.append(rec)

    return save_all_clients(items)

def update_account_in_db(client_name: str, updated: Dict) -> bool:
    """
    Update or insert an account record matching client_name (case-insensitive).
    """
    items = load_all_clients()
    key = _norm_name(client_name)
    updated = _compute_money_fields(dict(updated or {}))
    updated["Name"] = updated.get("Name", client_name)

    for i, it in enumerate(items):
        if _norm_name(it.get("Name")) == key:
            items[i] = {**it, **updated}
            break
    else:
        items.append(updated)

    return save_all_clients(items)

# ---------- Appointments ----------
def load_appointments() -> List[Dict]:
    """Return list of appointment dicts."""
    return _read_json(APPOINTMENTS_FILE)

def save_appointments(items: List[Dict]) -> bool:
    """Overwrite all appointments."""
    return _write_json(APPOINTMENTS_FILE, list(items or []))

def append_appointment(appt: Dict) -> Tuple[bool, List[Dict]]:
    """
    Append or update an appointment. De-duplicate by (Name, Date, Time).
    Returns (changed, new_list).
    """
    items = load_appointments()
    key = (
        _norm_name(appt.get("Name")),
        (appt.get("Appointment Date") or "").strip(),
        (appt.get("Appointment Time") or "").strip(),
    )
    changed = False
    for i, it in enumerate(items):
        k2 = (
            _norm_name(it.get("Name")),
            (it.get("Appointment Date") or "").strip(),
            (it.get("Appointment Time") or "").strip(),
        )
        if k2 == key:
            items[i] = {**it, **appt}
            changed = True
            break
    else:
        items.append(dict(appt))
        changed = True

    save_appointments(items)
    return changed, items

def delete_appointment(name: str, date: str, time: str) -> bool:
    key = (_norm_name(name), (date or "").strip(), (time or "").strip())
    new_items = []
    for it in load_appointments():
        k2 = (_norm_name(it.get("Name")),
              (it.get("Appointment Date") or "").strip(),
              (it.get("Appointment Time") or "").strip())
        if k2 != key:
            new_items.append(it)
    return save_appointments(new_items)
