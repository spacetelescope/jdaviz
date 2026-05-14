from jdaviz.core.loaders.importers.spectrum1d.spectrum1d import SpectrumImporter


def test_spectrum1d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum1d_cube):
    """Test _check_is_valid for SpectrumImporter: success and failure cases."""

    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return SpectrumImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=input_data)

    # Success: valid 1D spectrum
    importer = _create_importer(input_data=spectrum1d)
    assert importer._check_is_valid() == ''

    # Failure: extension choices cleared
    importer = _create_importer(input_data=spectrum1d)
    importer.input_has_extensions = True
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'

    # Failure: 3D flux rejected by 1D importer
    importer = _create_importer(input_data=spectrum1d)
    importer._input = spectrum1d_cube
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'All spectra must have 1D or 2D flux.'
