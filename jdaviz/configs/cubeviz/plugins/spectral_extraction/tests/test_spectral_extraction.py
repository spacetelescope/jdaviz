import pytest
from packaging.version import Version

import astropy
from astropy.nddata import NDDataArray, StdDevUncertainty

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

    # axes 0, 1 are the spatial ones here:
    collapsed_cube = spectral_cube.sum(axis=(0, 1))

    assert isinstance(spectral_cube, NDDataArray)
    assert isinstance(collapsed_cube, NDDataArray)
