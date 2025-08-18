# agent_actions.py
import os, json
from datetime import datetime, timedelta

# Try both DB modules to avoid import errors across your codebase
try:
    from data.data import insert_client
except Exception:
    insert_client = None
try:
    from data.database import insert_client as insert_client_db
except Exception:
    insert_client_db = None

# Optional PDF (fallbacks gracefully)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    _HAVE_RL = True
except Exception:
    _HAVE_RL = False

def _ensure_reports_dir():
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out_dir = os.path.join(desktop, "reports")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def _safe_name(s: str) -> str:
    s = s or "Unknown"
    return "".join(c for c in s if c.isalnum() or c in (" ", "_")).replace(" ", "_") or "Unknown"

# ---- Actions ----

def action_insert_db(agent, ctx: dict):
    data = dict(ctx.get("data") or {})
    name = data.get("Name", "Unknown")
    # best-effort insert with dual backends
    ok = False
    err = None
    try:
        if insert_client:
            insert_client(data)
            ok = True
        elif insert_client_db:
            insert_client_db(data)
            ok = True
        else:
            err = "No insert_client function available"
    except Exception as e:
        err = str(e)
    if not ok:
        return ctx, f"⚠️ DB insert skipped: {err}"
    return ctx, f"📥 Inserted client '{name}' into database"

def action_followup_rule(agent, ctx: dict):
    data = dict(ctx.get("data") or {})
    try:
        if not data.get("Follow-Up Date"):
            # default: 7 days after today's Date if present, else today+7
            base = datetime.today()
            try:
                base = datetime.strptime(data.get("Date",""), "%d-%m-%Y") or base
            except Exception:
                pass
            fut = base + timedelta(days=7)
            data["Follow-Up Date"] = fut.strftime("%d-%m-%Y")
            ctx["data"] = data
            return ctx, f"🗓️ Follow-up set to {data['Follow-Up Date']}"
        return ctx, "🗓️ Follow-up already set"
    except Exception as e:
        return ctx, f"⚠️ Follow-up rule error: {e}"

def action_tag_appointment_status(agent, ctx: dict):
    data = dict(ctx.get("data") or {})
    date = (data.get("Appointment Date") or "Not Specified").strip()
    time = (data.get("Appointment Time") or "Not Specified").strip()
    if date != "Not Specified" and time != "Not Specified":
        data["Status"] = "Scheduled"
    elif date != "Not Specified":
        data["Status"] = "Date only"
    else:
        data["Status"] = "No-appointment"
    ctx["data"] = data
    return ctx, f"🏷️ Status tagged: {data['Status']}"

def action_generate_pdf(agent, ctx: dict):
    data = dict(ctx.get("data") or {})
    name = _safe_name(data.get("Name","Unknown"))
    out_dir = _ensure_reports_dir()
    pdf_path = os.path.join(out_dir, f"{name}_report.pdf")
    if not _HAVE_RL:
        # fallback: create a tiny text file to avoid crashing
        with open(pdf_path.replace(".pdf",".txt"), "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
        ctx["pdf_path"] = pdf_path.replace(".pdf",".txt")
        return ctx, f"📝 ReportLab missing; wrote TXT: {ctx['pdf_path']}"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elems = []
    elems.append(Paragraph(f"Patient Report: {data.get('Name','Unknown')}", styles["Title"]))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("<b>Summary:</b><br/>" + (data.get("Summary","No summary")), styles["BodyText"]))
    elems.append(Spacer(1, 12))
    rows = [["Field", "Value"]]
    for k in ["Age","Symptoms","Notes","Date","Appointment Date","Appointment Time","Follow-Up Date","Status"]:
        v = data.get(k,"")
        if isinstance(v, list): v = ", ".join(map(str, v))
        rows.append([k, str(v)])
    table = Table(rows, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0), colors.HexColor('#4f46e5')),
        ('TEXTCOLOR',(0,0),(-1,0), colors.whitesmoke),
        ('GRID',(0,0),(-1,-1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elems.append(table)
    doc.build(elems)
    ctx["pdf_path"] = pdf_path
    return ctx, f"📄 PDF created: {pdf_path}"

def action_write_json(agent, ctx: dict):
    data = dict(ctx.get("data") or {})
    name = _safe_name(data.get("Name","Unknown"))
    out_dir = _ensure_reports_dir()
    json_path = os.path.join(out_dir, f"{name}_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    ctx["json_path"] = json_path
    return ctx, f"🗂️ JSON written: {json_path}"

# Provide both: individual symbols AND a convenience registrar
def register_actions(agent):
    agent.register_many({
        "insert_db": action_insert_db,
        "followup_rule": action_followup_rule,
        "tag_status": action_tag_appointment_status,
        "make_pdf": action_generate_pdf,
        "write_json": action_write_json,
    })
