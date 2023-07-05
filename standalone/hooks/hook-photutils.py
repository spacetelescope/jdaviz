from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("photutils")
# for CITATION.rst
datas = collect_data_files('photutils')
