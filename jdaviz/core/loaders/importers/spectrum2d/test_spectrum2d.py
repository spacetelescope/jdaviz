from jdaviz.core.loaders.importers.spectrum2d.spectrum2d import Spectrum2DImporter


def test_spectrum2d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum2d):
    """Test all string-returning scenarios in Spectrum2DImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Init with valid 2D spectrum, swap to 1D flux, clear cached spectra
    importer = Spectrum2DImporter(app=deconfigged_helper._app,
                                  resolver=resolver, parser=None,
                                  input=spectrum2d)
    importer._input = spectrum1d
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'Spectrum flux must be 2D.'
