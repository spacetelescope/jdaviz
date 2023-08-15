import pytest
from packaging.version import Version
import numpy as np
import astropy
from astropy.nddata import NDDataArray, StdDevUncertainty
from specutils import Spectrum1D
from regions import CirclePixelRegion, PixCoord

ASTROPY_LT_5_3_2 = Version(astropy.__version__) < Version('5.3.2')


@pytest.mark.skipif(not ASTROPY_LT_5_3_2, reason='Needs astropy <5.3.2')
def test_version_before_nddata_update(cubeviz_helper, spectrum1d_cube_with_uncerts):
    # Also test that plugin is disabled before data is loaded.
    plg = cubeviz_helper.plugins['Spectral Extraction']
    assert plg._obj.disabled_msg != ''


@pytest.mark.skipif(ASTROPY_LT_5_3_2, reason='Needs astropy 5.3.2 or later')
def test_version_after_nddata_update(cubeviz_helper, spectrum1d_cube_with_uncerts):
    # Also test that plugin is disabled before data is loaded.
    plg = cubeviz_helper.plugins['Spectral Extraction']
    assert plg._obj.disabled_msg == ''

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)

    spectral_cube = cubeviz_helper.app.data_collection[0].get_object(NDDataArray)
    uncert_cube = cubeviz_helper.app.data_collection[1].get_object(StdDevUncertainty)
    spectral_cube.uncertainty = uncert_cube

    # Collapse the spectral cube using the astropy.nddata machinery.
    # Axes 0, 1 are the spatial ones.
    collapsed_cube_nddata = spectral_cube.sum(axis=(0, 1))  # return NDDataArray

    # Collapse the spectral cube using the methods in jdaviz:
    collapsed_cube_s1d = plg.collapse_to_spectrum(add_data=False)  # returns Spectrum1D

    assert isinstance(spectral_cube, NDDataArray)
    assert isinstance(collapsed_cube_s1d, Spectrum1D)

    np.testing.assert_allclose(
        collapsed_cube_nddata.data,
        collapsed_cube_s1d.flux.to_value(collapsed_cube_nddata.unit)
    )


@pytest.mark.skipif(ASTROPY_LT_5_3_2, reason='Needs astropy 5.3.2 or later')
@pytest.mark.parametrize(
    "function, expected_uncert",
    zip(
        ["Sum", "Mean", "Min", "Max"],
        [2, 0.5, 1, 1]
    )
)
def test_subset(
    cubeviz_helper, spectrum1d_cube_with_uncerts, function, expected_uncert
):
    # give uniform unit uncertainties for this test:
    spectrum1d_cube_with_uncerts.uncertainty = StdDevUncertainty(
        np.ones_like(spectrum1d_cube_with_uncerts.data)
    )

    regions = [
        # create a subset with a single pixel:
        CirclePixelRegion(PixCoord(0, 1), radius=0.7),
        # two-pixel region:
        CirclePixelRegion(PixCoord(0.5, 0), radius=1.2)
    ]

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)
    cubeviz_helper.load_regions(regions)

    plg = cubeviz_helper.plugins['Spectral Extraction']
    plg.function = function

    # single pixel region:
    plg.spatial_subset = 'Subset 1'
    collapsed_spec_1 = plg.collapse_to_spectrum()

    # this single pixel has two wavelengths, and all uncertainties are unity
    # irrespective of which collapse function is applied:
    assert len(collapsed_spec_1.flux) == 2
    assert np.all(np.equal(collapsed_spec_1.uncertainty.array, 1))

    # this two-pixel region has four unmasked data points per wavelength:
    plg.spatial_subset = 'Subset 2'
    collapsed_spec_2 = plg.collapse_to_spectrum()

    assert np.all(np.equal(collapsed_spec_2.uncertainty.array, expected_uncert))
