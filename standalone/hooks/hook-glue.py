from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('glue')
datas += copy_metadata('glue-core')
