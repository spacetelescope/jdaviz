from jdaviz.core.loaders.importers.spectrum1d.spectrum1d import SpectrumImporter


def test_spectrum1d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum1d_cube):
    """Test _check_is_valid for SpectrumImporter: success and failure cases."""

    resolver = deconfigged_helper.loaders['object']._obj

    # Success: valid 1D spectrum
    importer = SpectrumImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=spectrum1d)
    assert importer._check_is_valid() == ''

    # Failure: 3D flux rejected by 1D importer
    # Must come before clearing extension.items since the extension check fires first
    importer._input = spectrum1d_cube
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'All spectra must have 1D or 2D flux.'

    # Failure: extension choices cleared
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'
