import pytest
from packaging.version import Version
import numpy as np
import astropy
from astropy.nddata import NDDataArray, StdDevUncertainty
from specutils import Spectrum1D

ASTROPY_LT_5_3_DEV = Version(astropy.__version__) < Version('5.3.dev')


@pytest.mark.skipif(ASTROPY_LT_5_3_DEV, reason='Needs astropy 5.3.dev or later')
def test_version_reqs(cubeviz_helper, spectrum1d_cube_with_uncert):
    # Also test that plugin is disabled before data is loaded.
    plg = cubeviz_helper.plugins['Spectral Extraction']
    assert plg._obj.disabled_msg == ''

    cubeviz_helper.load_data(spectrum1d_cube_with_uncert)

    spectral_cube = cubeviz_helper.app.data_collection[0].get_object(NDDataArray)
    uncert_cube = cubeviz_helper.app.data_collection[1].get_object(StdDevUncertainty)
    spectral_cube.uncertainty = uncert_cube

    # Collapse the spectral cube using the astropy.nddata machinery.
    # Axes 0, 1 are the spatial ones.
    collapsed_cube_nddata = spectral_cube.sum(axis=(0, 1))  # return NDDataArray

    # Collapse the spectral cube using the methods in jdaviz:
    collapsed_cube_s1d = plg.collapse_to_spectrum(add_data=True)  # returns Spectrum1D

    assert isinstance(spectral_cube, NDDataArray)
    assert isinstance(collapsed_cube_s1d, Spectrum1D)

    np.testing.assert_allclose(
        collapsed_cube_nddata.data,
        collapsed_cube_s1d.flux.to_value(collapsed_cube_nddata.unit)
    )
