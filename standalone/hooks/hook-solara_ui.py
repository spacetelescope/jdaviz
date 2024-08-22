from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("solara-ui")
datas = collect_data_files('solara-ui')
datas += copy_metadata('solara-ui')
