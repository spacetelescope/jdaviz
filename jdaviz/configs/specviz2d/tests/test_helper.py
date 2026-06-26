import os
import numpy as np
import pytest
from specutils import Spectrum

from jdaviz import Specviz

CI = os.environ.get("CI", "False").lower() == "true"


@pytest.mark.skipif(CI, reason="Temporarily skipped failing specviz2d test in CI")
def test_helper(deconfigged_helper, mos_spectrum2d):
    deconfigged_helper.load(spectrum_2d=mos_spectrum2d, format='2D Spectrum')
    assert isinstance(deconfigged_helper.specviz, Specviz)

    deconfigged_helper._app.data_collection[0].meta['Trace'] = "Test"

    # Test both the old and new API
    returned_data = deconfigged_helper.datasets["Spectrum 2D"].get_data()
    returned_data_old_api = deconfigged_helper.get_data("Spectrum 2D")

    assert len(returned_data.shape) == 1
    assert isinstance(returned_data, Spectrum)
    assert isinstance(returned_data_old_api, Spectrum)
    # Verify both APIs return equivalent data
    assert np.array_equal(returned_data.flux, returned_data_old_api.flux)


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(deconfigged_helper):
    for plugin_name, plugin_api in deconfigged_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
