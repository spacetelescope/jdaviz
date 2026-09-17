from PyInstaller.utils.hooks import collect_data_files, collect_entry_point

import importlib.metadata

datas = collect_data_files("asdf")
hiddenimports = []
provider_packages = set()

for group in ("asdf.extensions", "asdf.resource_mappings"):
    # ASDF discovers converters and resource mappings dynamically through
    # entry points. PyInstaller cannot infer those imports from source.
    entry_point_datas, entry_point_hiddenimports = collect_entry_point(group)
    datas += entry_point_datas
    hiddenimports += entry_point_hiddenimports

    # Entry-point metadata locates the providers, but their schemas and
    # manifests are package data and must also be collected explicitly.
    for entry_point in importlib.metadata.entry_points(group=group):
        provider_packages.add(entry_point.module.split(".", 1)[0])

for package in sorted(provider_packages):
    datas += collect_data_files(package)