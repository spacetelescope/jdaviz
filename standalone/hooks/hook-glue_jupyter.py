from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('glue_jupyter')
datas += copy_metadata('glue_jupyter')
