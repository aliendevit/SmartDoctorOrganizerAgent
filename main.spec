# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
# In .spec (Analysis section), add:
hiddenimports = [
    "MedicalDocAi.Tabs.extraction_tab",
    "MedicalDocAi.Tabs.dashboard_tab",
    "MedicalDocAi.Tabs.appointment_tab",
    "MedicalDocAi.Tabs.account_tab",
    "MedicalDocAi.Tabs.clients_stats_tab",
    "MedicalDocAi.model_intent.chatbot_tab",
    "MedicalDocAi.features.translation_helper",
    "MedicalDocAi.UI.design_system",
    "MedicalDocAi.UI.modern_theme",
]

