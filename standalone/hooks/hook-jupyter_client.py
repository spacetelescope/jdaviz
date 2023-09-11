from PyInstaller.utils.hooks import (collect_submodules,
                                     collect_data_files,
                                     copy_metadata)

datas = collect_data_files('jupyter_client')
datas += copy_metadata('jupyter_client')
hiddenimports = collect_submodules("jupyter_client")
