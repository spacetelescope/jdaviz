from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules, collect_all

# hiddenimports = collect_submodules("solara")

datas, binaries, hiddenimports = collect_all('solara')

# datas = collect_data_files('solara')
datas += collect_data_files('solara-ui')
