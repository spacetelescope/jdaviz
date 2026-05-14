from jdaviz.core.loaders.importers.spectrum1d.spectrum1d import SpectrumImporter


def test_spectrum1d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum1d_cube):
    """Test all string-returning scenarios in SpectrumImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Init with valid 1D spectrum, set input_has_extensions=True, clear choices
    importer = SpectrumImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=spectrum1d)
    importer.input_has_extensions = True
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'

    # Init with valid 1D spectrum, swap to 3D flux, clear cached spectra
    importer = SpectrumImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=spectrum1d)
    importer._input = spectrum1d_cube
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'All spectra must have 1D or 2D flux.'
