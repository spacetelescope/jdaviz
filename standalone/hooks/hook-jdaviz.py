from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('jdaviz')
datas += copy_metadata('jdaviz')
