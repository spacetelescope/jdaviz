from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("scipy")
datas = collect_data_files('scipy')
datas += copy_metadata('scipy')
