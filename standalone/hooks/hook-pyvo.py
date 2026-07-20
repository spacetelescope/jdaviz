from PyInstaller.utils.hooks import collect_data_files

# Collect all JSON files from pythreejs package
datas = collect_data_files('pyvo', includes=['**/*.png', '**/*.xml'])