from astropy.io import fits
from jdaviz.conftest import _generate_mos_spectrum2d
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
    importer._input = spectrum1d
    if 'spectra' in importer.__dict__:
        del importer.__dict__['spectra']
    assert importer._check_is_valid() == 'Spectrum flux must be 2D.'


def test_spectrum2d_transposed_input_data(deconfigged_helper):
    """
    Test that the transposed input data raises a banner/gets added to history
    and is handled correctly.
    """
    data, header = _generate_mos_spectrum2d()
    transposed_data = data.T

    # We have to go through the FITS parser to trigger the message
    hdu = fits.ImageHDU(transposed_data.value)
    hdu.header.update(header)

    hdulist = fits.HDUList([fits.PrimaryHDU(), hdu])
    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdulist

    expected_msg = 'Transposed input data'
    # Check banner
    assert any([expected_msg in msg['text']
                for msg in ldr.importer._obj.loader_message_items])
    # Check history
    assert any([expected_msg in msg['text']
                for msg in deconfigged_helper.plugins['Logger'].history])

    ldr.load()

    # Check that the data was transposed back to the original shape
    assert deconfigged_helper.get_data('2D Spectrum').data.shape == data.shape
    # Check that the message isn't duplicated in either banner or history
    assert sum(expected_msg in msg['text']
               for msg in ldr.importer._obj.loader_message_items) == 1
    assert sum(expected_msg in msg['text']
               for msg in deconfigged_helper.plugins['Logger'].history) == 1
