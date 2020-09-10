import pytest
import numpy as np

from astropy.utils.data import download_file

from jdaviz.app import Application

URL = 'https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits'


@pytest.fixture
def jdaviz_app():
    return Application(configuration='cubeviz')


def test_data_retrieval(jdaviz_app):

    fn = download_file(URL, cache=True)
    jdaviz_app.load_data(fn)

    # two ways of retrieving data from the viewer.
    # They should return the same spectral values
    a1 = jdaviz_app.get_viewer('spectrum-viewer').data()
    a2 = jdaviz_app.get_data_from_viewer("spectrum-viewer")

    test_value_1 = a1[0].data
    test_value_2 = list(a2.values())[0].data

    assert np.allclose(test_value_1, test_value_2, atol=1e-5)
