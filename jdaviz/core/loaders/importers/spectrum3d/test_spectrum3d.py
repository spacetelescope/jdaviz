from jdaviz.core.loaders.importers.spectrum3d.spectrum3d import Spectrum3DImporter


def test_spectrum3d_importer_is_valid(deconfigged_helper, spectrum1d, spectrum1d_cube):
    """Test _check_is_valid for Spectrum3DImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Success: valid 3D spectrum
    importer = Spectrum3DImporter(app=deconfigged_helper._app,
                                  resolver=resolver, parser=None,
                                  input=spectrum1d_cube)
    assert importer._check_is_valid() == ''

    # Failure: 1D flux rejected by 3D importer
    importer._input = spectrum1d
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'Spectrum flux must be 3D.'
