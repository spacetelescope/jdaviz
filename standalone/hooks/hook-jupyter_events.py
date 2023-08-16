from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('jupyter_events')
datas += copy_metadata('jupyter_events')
