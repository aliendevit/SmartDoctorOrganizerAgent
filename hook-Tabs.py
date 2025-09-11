# hook-Tabs.py
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Include all Python submodules under Tabs (handles dynamic imports)
hiddenimports = collect_submodules('Tabs')

# If your Tabs modules load any data files (qss/ui/json/etc.), include them too.
# Adjust patterns as needed.
datas = []
datas += collect_data_files('Tabs', includes=['*.qss', '*.ui', '*.json', '*.txt'])
