from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files("debugpy")
# we are picking up debugpy/_vendored/pydevd/pydevd_attach_to_process/attach_linux_amd64.dylib
datas = filter(lambda x: not x[0].endswith('.dylib'), datas)
# binaries = collect_dynamic_libs('omp')

# breakpoint()