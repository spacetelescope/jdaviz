from PyInstaller.utils.hooks import check_requirement, collect_data_files, copy_metadata, collect_submodules

hiddenimports = collect_submodules("scipy")
datas = collect_data_files('scipy')
datas += copy_metadata('scipy')

if check_requirement("scipy >= 1.14.0") and check_requirement("scipy < 1.18.0"): 
    hiddenimports += ['scipy._lib.array_api_compat.numpy.fft'] 
elif check_requirement("scipy >= 1.18.0"): 
    hiddenimports += ['scipy._external.array_api_compat.numpy.fft'] 