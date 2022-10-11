import numpy as np
import pytest
from astropy import units as u
from astropy.wcs import WCS
from specutils import Spectrum1D
from glue.core.roi import XRangeROI
from numpy.testing import assert_allclose

from jdaviz.utils import PRIHDR_KEY


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse(image_cube_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_cube_hdu_obj)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label == "Unknown HDU object[FLUX]"

    # first load should be successful; subsequent attempts should fail
    with pytest.raises(RuntimeError, match=r".?only one (data)?cube.?"):
        cubeviz_helper.load_data(image_cube_hdu_obj)


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_with_microns(image_cube_hdu_obj_microns, cubeviz_helper):
    # Passing in data_label keyword as posarg.
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, 'has_microns')

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label == 'has_microns[FLUX]'

    flux_cube = cubeviz_helper.app.data_collection[0].get_object(Spectrum1D, statistic=None)
    assert flux_cube.spectral_axis.unit == u.um

    # This tests the same data as test_fits_image_hdu_parse above.

    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'

    unc_viewer = cubeviz_helper.app.get_viewer('uncert-viewer')
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover.pixel == 'x=-1.0 y=00.0'
    assert unc_viewer.label_mouseover.value == ''  # Out of bounds


def test_spectrum1d_with_fake_fixed_units(spectrum1d, cubeviz_helper):
    header = {
        'WCSAXES': 1,
        'CRPIX1': 0.0,
        'CDELT1': 1E-06,
        'CUNIT1': 'm',
        'CTYPE1': 'WAVE',
        'CRVAL1': 0.0,
        'RADESYS': 'ICRS'}
    wcs = WCS(header)
    cubeviz_helper.app.add_data(spectrum1d, "test")

    dc = cubeviz_helper.app.data_collection
    dc[0].meta["_orig_wcs"] = wcs
    dc[0].meta["_orig_spec"] = spectrum1d

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'test')
    cubeviz_helper.app.get_viewer('spectrum-viewer').apply_roi(XRangeROI(6600, 7400))

    subsets = cubeviz_helper.app.get_subsets_from_viewer("spectrum-viewer")
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert_allclose(reg.lower.value, 6666.666666666667)
    assert_allclose(reg.upper.value, 7333.333333333334)
    assert reg.lower.unit == 'Angstrom'
    assert reg.upper.unit == 'Angstrom'


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse_from_file(tmpdir, image_cube_hdu_obj, cubeviz_helper):
    f = tmpdir.join("test_fits_image.fits")
    path = f.strpath
    image_cube_hdu_obj.writeto(path, overwrite=True)
    cubeviz_helper.load_data(path)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label == "test_fits_image.fits[FLUX]"

    # This tests the same data as test_fits_image_hdu_parse above.

    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'
    assert flux_viewer.label_mouseover.world_ra_deg == '205.4433848390'
    assert flux_viewer.label_mouseover.world_dec_deg == '26.9996149270'

    unc_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_uncert_viewer_reference_name)
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover.pixel == 'x=-1.0 y=00.0'
    assert unc_viewer.label_mouseover.value == ''  # Out of bounds
    assert unc_viewer.label_mouseover.world_ra_deg == '205.4441642302'
    assert unc_viewer.label_mouseover.world_dec_deg == '26.9996148973'


@pytest.mark.filterwarnings('ignore')
def test_spectrum3d_parse(image_cube_hdu_obj, cubeviz_helper):
    flux = image_cube_hdu_obj[1].data << u.Unit(image_cube_hdu_obj[1].header['BUNIT'])
    wcs = WCS(image_cube_hdu_obj[1].header, image_cube_hdu_obj)
    sc = Spectrum1D(flux=flux, wcs=wcs)
    cubeviz_helper.load_data(sc)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label == "Unknown spectrum object[FLUX]"

    # Same as flux viewer data in test_fits_image_hdu_parse_from_file
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'
    assert flux_viewer.label_mouseover.world_ra_deg == '205.4433848390'
    assert flux_viewer.label_mouseover.world_dec_deg == '26.9996149270'

    # These viewers have no data.

    unc_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_uncert_viewer_reference_name)
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover is None


def test_spectrum1d_parse(spectrum1d, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('Spectrum1D')
    assert cubeviz_helper.app.data_collection[0].meta['uncertainty_type'] == 'std'

    # Coordinate display is only for spatial image, which is missing here.
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    assert flux_viewer.label_mouseover is None


def test_numpy_cube(cubeviz_helper):
    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones(27).reshape((3, 3, 3)))
