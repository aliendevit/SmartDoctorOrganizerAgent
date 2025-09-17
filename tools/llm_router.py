# tools/llm_router.py
import json, re
from datetime import datetime
from typing import Dict, Any, Optional, List

from nlp.gemma_text import generate
from data.appointments import appointments_on

# --- tool registry ---
def tool_get_appointments(date: str = "today", order: str = "asc", limit: int = 10) -> List[Dict[str, Any]]:
    if date.lower() == "today":
        day = datetime.now()
    else:
        # accept dd-mm-yyyy / yyyy-mm-dd
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                day = datetime.strptime(date, fmt)
                break
            except Exception:
                day = None
        if not day:
            day = datetime.now()
    items = appointments_on(day)
    if order.lower().startswith("desc"): items = list(reversed(items))
    if isinstance(limit, int) and limit > 0: items = items[:limit]
    # Strip helper keys
    for it in items:
        it.pop("_time", None); it.pop("_src", None)
    return items

TOOLS = {
    "get_appointments": tool_get_appointments,
}

# --- planner prompt ---
PLANNER = """You are a tool-using assistant. Decide whether to call a tool.
Valid tools:
- get_appointments(date: string, order: "asc"|"desc", limit: int)

Return STRICT JSON with no prose. Schema:
{"action":"tool_call","tool":"get_appointments","args":{"date":"today","order":"desc","limit":1}}
or
{"action":"answer","text":"...final answer without tools..."}

User: {query}
JSON:
"""

RX_OBJ = re.compile(r"\{[\s\S]*\}$")

def plan_action(query: str) -> Dict[str, Any]:
    raw = generate(PLANNER.format(query=query), max_new_tokens=256)
    m = RX_OBJ.search(raw)
    js = m.group(0) if m else raw
    try:
        obj = json.loads(js)
        # light validation
        if obj.get("action") not in ("tool_call","answer"):
            raise ValueError("bad action")
        return obj
    except Exception:
        # fallback: safely prefer a single appointment tool call for “last appointment today”
        return {"action":"tool_call","tool":"get_appointments","args":{"date":"today","order":"desc","limit":1}}

# --- finalizer prompt ---
FINALIZER = """You are formatting an answer for the user based on TOOL_RESULT.
Keep it concise and helpful.

USER QUESTION:
{query}

TOOL_RESULT (JSON):
{tool_json}

Write the final answer:
"""

def answer_with_tools(user_text: str) -> str:
    plan = plan_action(user_text)
    if plan["action"] == "answer":
        return plan.get("text","")

    # tool_call path
    tool = TOOLS.get(plan.get("tool",""))
    if not tool:
        return "Sorry, I don’t have that tool."

    args = dict(plan.get("args") or {})
    try:
        result = tool(**args)
    except TypeError:
        # sanitize unexpected args
        result = tool(date=args.get("date","today"),
                      order=args.get("order","asc"),
                      limit=int(args.get("limit",10) or 10))

    # second pass: format the final answer
    tool_json = json.dumps(result, ensure_ascii=False, indent=2)
    final = generate(FINALIZER.format(query=user_text, tool_json=tool_json), max_new_tokens=256)
    return final.strip() or "Done."
