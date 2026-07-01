from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_all


datas, binaries, hiddenimports = collect_all('glue')

# datas = collect_data_files('glue')
datas += copy_metadata('glue-core')
# hiddenimports += [