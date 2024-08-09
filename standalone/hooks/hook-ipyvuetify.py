from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("ipyvuetify")
datas = collect_data_files('ipyvuetify')
datas += copy_metadata('ipyvuetify')
