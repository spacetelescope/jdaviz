from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("astroquery")
datas = collect_data_files('astroquery')
datas += copy_metadata('astroquery')
