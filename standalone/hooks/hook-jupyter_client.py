from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("jupyter_client")
