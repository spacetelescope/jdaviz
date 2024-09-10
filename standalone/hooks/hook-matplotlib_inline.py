from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('matplotlib_inline')
# since matplotlib 3.9 entry_points.txt is needed
datas += copy_metadata('matplotlib_inline')
