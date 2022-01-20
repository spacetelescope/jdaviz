""" The purpose of this test is to check that both methods:

      - app.get_viewer('spectrum-viewer').data()
      - app.get_data_from_viewer("spectrum-viewer")

      return the same spectrum values.
"""
import numpy as np
import pytest
from astropy.utils.data import download_file


@pytest.mark.filterwarnings('ignore')
@pytest.mark.remote_data
def test_data_retrieval(cubeviz_app):
    # This file is originally from
    # https://data.sdss.org/sas/dr14/manga/spectro/redux/v2_1_2/7495/stack/manga-7495-12704-LOGCUBE.fits.gz
    URL = 'https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits'

    fn = download_file(URL, cache=True)
    cubeviz_app.load_data(fn)

    # two ways of retrieving data from the viewer.
    # They should return the same spectral values
    a1 = cubeviz_app.app.get_viewer('spectrum-viewer').data()
    a2 = cubeviz_app.app.get_data_from_viewer("spectrum-viewer")

    test_value_1 = a1[0].data
    test_value_2 = list(a2.values())[0].data

    assert np.allclose(test_value_1, test_value_2, atol=1e-5)
