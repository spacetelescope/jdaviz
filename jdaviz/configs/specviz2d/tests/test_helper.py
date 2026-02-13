import pytest
from specutils import Spectrum

from jdaviz import Specviz
from jdaviz.core.user_api import DataApi, SpectralDataApi


def test_helper(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d)
    assert isinstance(specviz2d_helper.specviz, Specviz)

    specviz2d_helper.app.data_collection[0].meta['Trace'] = "Test"

    returned_data = specviz2d_helper.get_data("Spectrum 2D")
    assert len(returned_data.shape) == 1
    assert isinstance(returned_data, Spectrum)


# Some API might be going through deprecation, so ignore the warning.
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_plugin_user_apis(specviz2d_helper):
    for plugin_name, plugin_api in specviz2d_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_data_access_deconfigged(deconfigged_helper, mos_spectrum2d):
    """Test the .data property access for the deconfigged helper."""
    # Initially no data loaded
    assert deconfigged_helper.data == {}
    assert deconfigged_helper.data_labels == []

    # Load data
    deconfigged_helper.load(mos_spectrum2d, data_label='Test 2D Spectrum',
                            format='2D Spectrum', auto_extract=True)

    # Test data_labels property
    assert 'Test 2D Spectrum' in deconfigged_helper.data_labels
    assert 'Test 2D Spectrum (auto-ext)' in deconfigged_helper.data_labels
    assert len(deconfigged_helper.data_labels) == 2

    # Test data property returns dict of DataApi objects
    data_dict = deconfigged_helper.data
    assert isinstance(data_dict, dict)
    assert 'Test 2D Spectrum' in data_dict
    assert 'Test 2D Spectrum (auto-ext)' in data_dict

    # Test that spectral data uses SpectralDataApi (subclass of DataApi)
    assert isinstance(data_dict['Test 2D Spectrum'], DataApi)
    assert isinstance(data_dict['Test 2D Spectrum'], SpectralDataApi)
    assert isinstance(data_dict['Test 2D Spectrum (auto-ext)'], SpectralDataApi)

    # Test DataApi.get_object() returns Spectrum
    spectrum_obj = data_dict['Test 2D Spectrum'].get_object()
    assert isinstance(spectrum_obj, Spectrum)

    # Test that SpectralDataApi accepts spectral_subset argument (even if None)
    spectrum_no_subset = data_dict['Test 2D Spectrum (auto-ext)'].get_object(spectral_subset=None)
    assert isinstance(spectrum_no_subset, Spectrum)

    # Test add_to_viewer method
    # Get current viewer references
    viewer_1d = deconfigged_helper.viewers['1D Spectrum']

    # Remove data from viewer to test add_to_viewer
    viewer_1d.data_menu.remove_data('Test 2D Spectrum (auto-ext)')
    assert 'Test 2D Spectrum (auto-ext)' not in viewer_1d.data_menu.layer.choices
    data_dict['Test 2D Spectrum (auto-ext)'].add_to_viewer('1D Spectrum')
    assert 'Test 2D Spectrum (auto-ext)' in viewer_1d.data_menu.layer.choices

    # Test add_to_viewer with invalid data for viewer raises error
    with pytest.raises(ValueError, match="not one of the valid data"):
        data_dict['Test 2D Spectrum'].add_to_viewer('1D Spectrum')
