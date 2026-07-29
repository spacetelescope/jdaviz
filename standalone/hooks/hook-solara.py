from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules, collect_all

datas, binaries, hiddenimports = collect_all('solara')
datas += copy_metadata('solara')
