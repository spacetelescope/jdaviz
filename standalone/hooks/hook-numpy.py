from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("numpy")
datas = collect_data_files('numpy')
datas += copy_metadata('numpy')
