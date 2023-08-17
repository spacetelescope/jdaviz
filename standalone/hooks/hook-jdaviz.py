from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("jdaviz")
datas = collect_data_files('jdaviz')
datas += copy_metadata('jdaviz')
