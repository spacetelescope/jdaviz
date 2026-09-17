from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all, copy_metadata

hiddenimports = collect_submodules('s3fs') + collect_submodules('fsspec')
# for CITATION.rst
datas = collect_data_files('s3fs')
datas += copy_metadata('s3fs')
