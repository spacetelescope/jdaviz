from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('specreduce')
datas += copy_metadata('specreduce')
