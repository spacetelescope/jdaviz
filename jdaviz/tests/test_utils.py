import os
import warnings

import photutils
import pytest
from asdf.exceptions import AsdfWarning
from astropy import units as u
from astropy.utils import minversion
from astropy.wcs import FITSFixedWarning
from numpy.testing import assert_allclose
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import PIX2
from jdaviz.utils import (alpha_index, download_uri_to_path, flux_conversion,
                          _indirect_conversion, _eqv_pixar_sr)

PHOTUTILS_LT_1_12_1 = not minversion(photutils, "1.12.1.dev")


def test_spec_sb_flux_conversion():
    # Actual spectrum content does not matter, just the meta is used here.
    spec = Spectrum1D(flux=[1, 1, 1] * u.Jy, spectral_axis=[1, 2, 3] * u.um)

    # values != 2
    values = [10, 20, 30]

    # Float scalar pixel scale factor
    spec.meta["_pixel_scale_factor"] = 0.1
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec), [1, 2, 3])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec), [100, 200, 300])

    # conversions with eq pixels
    assert_allclose(flux_conversion(values, u.Jy / PIX2, u.Jy, spec), [10, 20, 30])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / PIX2, spec), [10, 20, 30])

    # complex translation Jy / sr -> erg / (Angstrom s cm2 sr)
    targ = [2.99792458e-12, 1.49896229e-12, 9.99308193e-13] * (u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr))  # noqa: E501
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr), spec), targ.value)  # noqa: E501
    # swap sr for pix2 and check conversion
    assert_allclose(flux_conversion(values, u.Jy / PIX2, u.erg / (u.Angstrom * u.s * u.cm**2 * PIX2), spec), targ.value)  # noqa: E501

    # complex translation erg / (Angstrom s cm2 sr) -> Jy / sr
    targ = [3.33564095e+13, 2.66851276e+14, 9.00623057e+14] * (u.Jy / u.sr)
    assert_allclose(flux_conversion(values, u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr), u.Jy / u.sr, spec), targ.value)  # noqa: E501
    # swap sr for pix2 and check conversion
    assert_allclose(flux_conversion(values, u.erg / (u.Angstrom * u.s * u.cm**2 * PIX2), u.Jy / PIX2, spec), targ.value)  # noqa: E501

    spectral_values = spec.spectral_axis
    spec_unit = u.MJy
    eqv = u.spectral_density(spectral_values) + _eqv_pixar_sr(spec.meta["_pixel_scale_factor"])

    # test spectrum when target unit in untranslatable unit list
    target_values = [5.03411657e-05, 2.01364663e-04, 4.53070491e-04]
    expected_units = (u.ph / (u.Hz * u.s * u.cm**2))
    for solid_angle in [u.sr, PIX2]:
        returned_values, return_units, unit_flag = _indirect_conversion(
                                                        values=values, orig_units=(u.MJy),
                                                        targ_units=(u.ph / (u.s * u.cm**2 * u.Hz * solid_angle)),  # noqa
                                                        eqv=eqv,
                                                        spec_unit=spec_unit,
                                                        indirect_needs_spec_axis=None
                                                    )
        assert_allclose(returned_values, target_values)
        assert (return_units == expected_units)
        assert (unit_flag == 'orig')

    # test spectrum when original unit in untranslatable unit list
    target_values = [1., 2., 3.]
    expected_units = (u.ph / (u.Angstrom * u.s * u.cm**2))
    returned_values, return_units, unit_flag = _indirect_conversion(
                                                    values=values,
                                                    orig_units=(u.ph / (u.Angstrom * u.s * u.cm**2 * u.sr)),  # noqa
                                                    targ_units=(u.MJy), eqv=eqv,
                                                    spec_unit=spec_unit, indirect_needs_spec_axis=None  # noqa
                                                )
    assert_allclose(returned_values, target_values)
    assert (return_units == expected_units)
    assert (unit_flag == 'targ')

    # test the default case where units are translatable
    target_values = [10, 20, 30]
    expected_units = (u.MJy)
    returned_values, return_units, unit_flag = _indirect_conversion(
                                                    values=values, orig_units=(u.Jy/u.sr),
                                                    targ_units=(u.MJy), eqv=eqv,
                                                    spec_unit=spec_unit, indirect_needs_spec_axis=None  # noqa
                                                )
    assert_allclose(returned_values, target_values)
    assert (return_units == expected_units)
    assert (unit_flag == 'targ')

    # test image viewer data units are untranslatable
    target_value = 1.e-18
    expected_units = (u.erg / (u.s * u.cm**2 * u.Hz))
    returned_values, return_units = _indirect_conversion(
                                        values=1, orig_units=(u.MJy/u.sr),
                                        targ_units=(u.erg / (u.s * u.cm**2 * u.Hz * u.sr)),
                                        eqv=eqv, spec_unit=None, indirect_needs_spec_axis=True
                                    )
    assert_allclose(returned_values, target_value)
    assert return_units == expected_units

    # test image viewer data units are translatable
    target_value = 10
    expected_units = (u.MJy / u.sr)
    returned_values, return_units = _indirect_conversion(
                                        values=10, orig_units=(u.MJy/u.sr), targ_units=(u.Jy/u.sr),
                                        eqv=eqv, spec_unit=None, indirect_needs_spec_axis=True
                                    )
    assert_allclose(returned_values, target_value)
    assert return_units == expected_units

    # Quantity scalar pixel scale factor
    spec.meta["_pixel_scale_factor"] = 0.1 * (u.sr / u.pix)
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec), [1, 2, 3])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec), [100, 200, 300])

    # values == 2
    values = [10, 20]
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec), [1, 2])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec), [100, 200])

    # float array pixel scale factor
    spec.meta["_pixel_scale_factor"] = [0.1, 0.2, 0.3]  # min_max = [0.1, 0.3]
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec), [1, 6])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec), [100, 66.66666666666667])

    # Quantity array pixel scale factor
    spec.meta["_pixel_scale_factor"] = [0.1, 0.2, 0.3] * (u.sr / u.pix)  # min_max = [0.1, 0.3]
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec), [1, 6])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec), [100, 66.66666666666667])

    # values != 2
    values = [10, 20, 30]
    spec.meta["_pixel_scale_factor"] = [0.1, 0.2, 0.3]
    assert_allclose(flux_conversion(values, u.Jy / u.sr, u.Jy, spec=spec), [1, 4, 9])
    assert_allclose(flux_conversion(values, u.Jy, u.Jy / u.sr, spec=spec), 100)

    # values != 2 but _pixel_scale_factor size mismatch
    with pytest.raises(ValueError, match="operands could not be broadcast together"):
        spec.meta["_pixel_scale_factor"] = [0.1, 0.2, 0.3, 0.4]
        flux_conversion(values, u.Jy / u.sr, u.Jy, spec=spec)

    # Other kind of flux conversion unrelated to _pixel_scale_factor.
    # The answer was obtained from synphot unit conversion.
    spec.meta["_pixel_scale_factor"] = 0.1
    targ = [2.99792458e-12, 1.49896229e-12, 9.99308193e-13] * (u.erg / (u.AA * u.cm * u.cm * u.s))  # FLAM  # noqa: E501
    assert_allclose(flux_conversion(values, u.Jy, targ.unit, spec=spec), targ.value)

    # values == 2 (only used spec.spectral_axis[0] for some reason)
    values = [10, 20]
    targ = [2.99792458e-12, 5.99584916e-12] * (u.erg / (u.AA * u.cm * u.cm * u.s))  # FLAM
    assert_allclose(flux_conversion(values, u.Jy, targ.unit, spec=spec), targ.value)


@pytest.mark.parametrize("test_input,expected", [(0, 'a'), (1, 'b'), (25, 'z'), (26, 'aa'),
                                                 (701, 'zz'), (702, '{a')])
def test_alpha_index(test_input, expected):
    assert alpha_index(test_input) == expected


def test_alpha_index_exceptions():
    with pytest.raises(TypeError, match="index must be an integer"):
        alpha_index(4.2)
    with pytest.raises(ValueError, match="index must be positive"):
        alpha_index(-1)


def test_uri_to_download_bad_scheme(imviz_helper):
    uri = "file://path/to/file.fits"
    with pytest.raises(ValueError, match=r'URI file://path/to/file\.fits with scheme file'):
        imviz_helper.load_data(uri)


@pytest.mark.remote_data
def test_uri_to_download_nonexistent_mast_file(imviz_helper):
    # this validates as a mast uri but doesn't actually exist on mast:
    uri = "mast:JWST/product/jw00000-no-file-here.fits"
    with pytest.raises(ValueError, match='Failed query for URI'):
        imviz_helper.load_data(uri, cache=False)


@pytest.mark.remote_data
def test_url_to_download_imviz_local_path_warning(imviz_helper):
    url = "https://www.astropy.org/astropy-data/tutorials/FITS-images/HorseHead.fits"
    match_local_path_msg = (
        'You requested to cache data to the .*local_path.*supported for downloads of '
        'MAST URIs.*astropy download cache instead.*'
    )
    with (
        pytest.warns(FITSFixedWarning, match="'datfix' made the change"),
        pytest.warns(UserWarning, match=match_local_path_msg)
    ):
        imviz_helper.load_data(url, cache=True, local_path='horsehead.fits')


def test_uri_to_download_specviz_local_path_check():
    uri = "mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits"
    local_path = download_uri_to_path(uri, cache=False, dryrun=True)  # No download

    # Wrong: '.\\JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits'
    # Correct:  '.\\jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits'
    assert local_path == os.path.join(os.curdir, "jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits")  # noqa: E501


@pytest.mark.remote_data
def test_uri_to_download_specviz(specviz_helper, tmp_path):
    uri = "mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits"
    local_path = str(tmp_path / uri.split('/')[-1])
    specviz_helper.load_data(uri, cache=True, local_path=local_path)


@pytest.mark.skip(reason="FIXME: Find a file that is not missing from MAST")
@pytest.mark.remote_data
def test_uri_to_download_specviz2d(specviz2d_helper, tmp_path):
    uri = "mast:JWST/product/jw01324-o006_s00005_nirspec_f100lp-g140h_s2d.fits"
    local_path = str(tmp_path / uri.split('/')[-1])

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', AsdfWarning)
        specviz2d_helper.load_data(uri, cache=True, local_path=local_path)
