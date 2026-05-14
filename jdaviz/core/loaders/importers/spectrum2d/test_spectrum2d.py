from jdaviz.core.loaders.importers.spectrum2d.spectrum2d import Spectrum2DImporter


def test_spectrum2d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum2d):
    """Test _check_is_valid for Spectrum2DImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Success: valid 2D spectrum
    importer = Spectrum2DImporter(app=deconfigged_helper._app,
                                  resolver=resolver, parser=None,
                                  input=spectrum2d)
    assert importer._check_is_valid() == ''

    # Failure: 1D flux rejected by 2D importer
    importer = Spectrum2DImporter(app=deconfigged_helper._app,
                                  resolver=resolver, parser=None,
                                  input=spectrum2d)
    importer._input = spectrum1d
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'Spectrum flux must be 2D.'
