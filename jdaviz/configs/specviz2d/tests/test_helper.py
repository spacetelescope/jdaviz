import numpy as np
import pytest
from specutils import Spectrum

from jdaviz import Specviz


def test_helper(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d)
    assert isinstance(specviz2d_helper.specviz, Specviz)

    specviz2d_helper.app.data_collection[0].meta['Trace'] = "Test"

    # Test both the old and new API
    returned_data = specviz2d_helper.datasets["Spectrum 2D"].get_data()
    returned_data_old_api = specviz2d_helper.get_data("Spectrum 2D")

    assert len(returned_data.shape) == 1
    assert isinstance(returned_data, Spectrum)
    assert isinstance(returned_data_old_api, Spectrum)
    # Verify both APIs return equivalent data
    assert np.array_equal(returned_data.flux, returned_data_old_api.flux)


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(specviz2d_helper):
    for plugin_name, plugin_api in specviz2d_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
