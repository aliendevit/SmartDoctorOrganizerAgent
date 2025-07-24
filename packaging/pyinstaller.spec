# pyinstaller.spec
block_cipher = None
import os
from PyInstaller.utils.hooks import collect_submodules

hidden = []
hidden += collect_submodules('dateparser')
hidden += collect_submodules('reportlab')
hidden += collect_submodules('matplotlib')  # harmless if not installed

a = Analysis(
    ['-m', 'app'],          # ✅ use __main__.py entry
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/icons', 'resources/icons'),
        ('json', 'json'),   # include archive folder
    ],
    hiddenimports=hidden,
    hookspath=['packaging'],
    runtime_hooks=[],
    excludes=['torch', 'tensorflow'],  # optional trim
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts,
    name='ClinicAssistant',
    debug=False, strip=False, upx=False,
    console=False,  # set True for debugging
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    name='ClinicAssistant'
)
