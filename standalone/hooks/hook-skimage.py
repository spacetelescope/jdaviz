from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files("skimage", includes=["*.pyi"])
# osx does not like the .dylib directory with signing
# [('.../site-packages/skimage/.dylibs/libomp.dylib', 'skimage/.dylibs')]
binaries = collect_dynamic_libs('skimage')
if binaries and binaries[0][0].endswith('.dylib'):
    assert len(binaries) == 1
    assert binaries[0][0].endswith('.dylibs/libomp.dylib')
    binaries = [
        (binaries[0][0], 'skimage'),
    ]
