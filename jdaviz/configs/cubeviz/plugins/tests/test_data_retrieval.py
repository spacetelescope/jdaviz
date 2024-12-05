import warnings

import pytest
import numpy as np

from astropy.utils.data import download_file


@pytest.mark.remote_data
def test_data_retrieval(cubeviz_helper):
    """The purpose of this test is to check that both methods:

    - app.get_viewer('spectrum-viewer').data()
    - cubeviz_helper.get_data()

    return the same spectrum values.
    """
    # This file is originally from
    # https://data.sdss.org/sas/dr17/manga/spectro/redux/v3_1_1/9862/stack/manga-9862-12703-LOGCUBE.fits.gz
    # (Updated to a newer file 11/19/2024)
    URL = 'https://stsci.box.com/shared/static/gts87zqt5265msuwi4w5u003b6typ6h0.gz'

    spectrum_viewer_reference_name = "spectrum-viewer"
    fn = download_file(URL, cache=True)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        cubeviz_helper.load_data(fn)

    # two ways of retrieving data from the viewer.
    # They should return the same spectral values
    a1 = cubeviz_helper.app.get_viewer(spectrum_viewer_reference_name).data()
    a2 = cubeviz_helper.get_data("Spectrum (sum)")

    test_value_1 = a1[0].data
    test_value_2 = a2.flux.value

    assert np.allclose(test_value_1, test_value_2, atol=1e-5)
