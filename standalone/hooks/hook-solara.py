from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("solara")
datas = collect_data_files('solara')
datas += collect_data_files('solara-ui')
