from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("ipyvuetify")
datas = collect_data_files('ipyvuetify')
datas += copy_metadata('ipyvuetify')

vue_datas, binaries, vue_hidden = collect_all('ipyvue')

datas += vue_datas
hiddenimports += vue_hidden