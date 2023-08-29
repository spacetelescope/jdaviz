from PyInstaller.utils.hooks import collect_submodules, collect_data_files

datas = collect_data_files('jupyter_server')
hiddenimports = collect_submodules("jupyter_server")
