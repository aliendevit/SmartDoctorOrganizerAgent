# PyInstaller hook for reportlab to include fonts and resources
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
hiddenimports = collect_submodules('reportlab')
datas = collect_data_files('reportlab')
