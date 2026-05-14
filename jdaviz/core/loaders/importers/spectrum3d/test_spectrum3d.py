from jdaviz.core.loaders.importers.spectrum3d.spectrum3d import Spectrum3DImporter


def test_spectrum3d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum1d_cube):
    """Test all string-returning scenarios in Spectrum3DImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Init with valid 3D spectrum, swap to 1D flux, clear cached spectra
    importer = Spectrum3DImporter(app=deconfigged_helper._app,
                                  resolver=resolver, parser=None,
                                  input=spectrum1d_cube)
    importer._input = spectrum1d
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'Spectrum flux must be 3D.'
