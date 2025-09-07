def ensure_theme(app):
    # Placeholder: Ensure a fallback Qt style if custom themes fail
    try:
        app.setStyle("Fusion")
    except Exception:
        pass
