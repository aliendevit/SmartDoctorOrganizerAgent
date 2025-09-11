import re
PATTERNS = [
    r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
    r"\b(?:\+?\d{1,2}\s?)?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
]
def redact(text: str, token="[REDACTED]") -> str:
    s = text
    for p in PATTERNS:
        s = re.sub(p, token, s)
    return s
