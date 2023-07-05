from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("regions")
# for CITATION.rst
datas = collect_data_files('regions')
