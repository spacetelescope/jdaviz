from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("solara-server")
datas = collect_data_files('solara-server')
datas += copy_metadata('solara-server')
