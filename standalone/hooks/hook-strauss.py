from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('strauss')
datas += copy_metadata('strauss')
