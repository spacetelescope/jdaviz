"""PyInstaller hook for pythreejs.

pythreejs requires JSON data files at runtime for shader definitions.
This hook ensures those files are bundled with the application.
"""

from PyInstaller.utils.hooks import collect_data_files

# Collect all JSON files from pythreejs package
datas = collect_data_files('pythreejs', includes=['**/*.json'])
