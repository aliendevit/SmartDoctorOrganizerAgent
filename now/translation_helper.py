import json, os

current_lang = "en"  # Global language; can be "en" or "ar"

def load_translations():
    translations_path = os.path.join(os.path.dirname(__file__), "translations.json")
    try:
        with open(translations_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Error loading translations:", e)
        return {}

translations = load_translations()

def tr(text):
    """Return the translation for 'text' based on current_lang; if not found, return original."""
    if text in translations:
        return translations[text].get(current_lang, text)
    return text
