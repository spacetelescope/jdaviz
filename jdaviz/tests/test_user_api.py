from specutils import Spectrum
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
from jdaviz.core.user_api import DataApi, SpectralDataApi, SpatialDataApi, SpectralSpatialDataApi
import pytest
import re


# This applies to all viz but testing with Imviz should be enough.
class TestImviz_WCS_WCS(BaseImviz_WCS_WCS):
    def test_imviz_zoom_level(self):
        v = self.imviz.viewers['imviz-0']
        assert v._obj.glue_viewer.state.x_min == -0.5
        assert v._obj.glue_viewer.state.x_max == 9.5

        v.zoom(2)

        assert v._obj.glue_viewer.state.x_min == 1.5
        assert v._obj.glue_viewer.state.x_max == 6.5

    def test_imviz_viewers(self):
        self.imviz.create_image_viewer()
        self.imviz.create_image_viewer()

        # regression test for https://github.com/spacetelescope/jdaviz/pull/2624
        assert len(self.imviz.viewers) == 3


def test_specviz_zoom_level(specviz_helper):
    v = specviz_helper.viewers['spectrum-viewer']
    v.set_limits(x_min=1, x_max=2, y_min=1, y_max=2)
    assert v._obj.glue_viewer.state.x_min == 1
    assert v._obj.glue_viewer.state.x_max == 2
    assert v._obj.glue_viewer.state.y_min == 1
    assert v._obj.glue_viewer.state.y_max == 2


def test_specviz_data_labels(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    assert list(specviz_helper.datasets.keys()) == [label]
    assert specviz_helper.viewers['spectrum-viewer'].data_menu.data_labels_loaded == [label]
    assert specviz_helper.viewers['spectrum-viewer'].data_menu.data_labels_visible == [label]


def test_toggle_api_hints(specviz_helper):
    assert specviz_helper.app.state.show_api_hints is False
    specviz_helper.toggle_api_hints()
    assert specviz_helper.app.state.show_api_hints is True
    specviz_helper.toggle_api_hints(True)
    assert specviz_helper.app.state.show_api_hints is True
    specviz_helper.toggle_api_hints()
    assert specviz_helper.app.state.show_api_hints is False


def test_wildcard_match_extensions(specviz_helper, premade_spectrum_list):
    """
    Test wildcard matching for source selection in Specviz. This tests setting
    the selection directly as opposed to using ``load``, via ``ldr.importer.extension``
    (whereas in the following test this is done through ``user_api.extension``, same idea).
    """
    default_choices = ['1D Spectrum at index: 0',
                       '1D Spectrum at index: 1',
                       'Exposure 0, Source ID: 0000',
                       'Exposure 0, Source ID: 1111',
                       'Exposure 1, Source ID: 1111']

    # Testing directly
    ldr = specviz_helper.loaders['object']
    ldr.object = premade_spectrum_list
    selection_obj = ldr.importer.extension
    assert selection_obj.selected == [default_choices[0]]
    assert selection_obj.choices == default_choices
    # Resetting to empty
    selection_obj.selected = []

    err_str1 = "not all items in"
    err_str2 = f"are one of {selection_obj.choices}, reverting selection to []"
    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *'] {err_str2}")):
        ldr.importer.extension = 'bad *'

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *', '* result'] {err_str2}")):
        ldr.importer.extension = ['bad *', '* result']

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['another', 'bad * result'] {err_str2}")):
        ldr.importer.extension = ['another', 'bad * result']

    # Check that selected is still/reverted successfully to []
    assert selection_obj.selected == []

    # This should get set to True automatically when multiple selections are made
    selection_obj.multiselect = False
    ldr.importer._obj.user_api.extension = '*'
    assert selection_obj.selected == selection_obj.choices
    assert selection_obj.multiselect is True


def test_wildcard_match_extension(imviz_helper, multi_extension_image_hdu_wcs):
    """
    Test wildcard matching for source selection in Specviz. This tests setting
    the selection directly as opposed to using ``load``, via
    ``ldr.importer._obj.user_api.extensions`` (whereas in the previous test this is
    done through ``user_api.extension``, same idea).
    """
    default_choices = ['1: [SCI,1]',
                       '2: [MASK,1]',
                       '3: [ERR,1]',
                       '4: [DQ,1]']

    # Testing directly
    ldr = imviz_helper.loaders['object']
    ldr.object = multi_extension_image_hdu_wcs
    selection_obj = ldr.importer.extension

    # Default selection
    assert selection_obj.selected == [default_choices[0]]

    # Resetting to []
    # Note this can't be done by setting selected = [], is this intentional?
    selection_obj.selected.pop(0)
    assert selection_obj.selected == []
    assert selection_obj.choices == default_choices

    err_str1 = "not all items in"
    err_str2 = f"are one of {selection_obj.choices}, reverting selection to []"
    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *'] {err_str2}")):
        ldr.importer._obj.user_api.extension = 'bad *'

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['bad *', '* result'] {err_str2}")):
        ldr.importer._obj.user_api.extension = ['bad *', '* result']

    with pytest.raises(ValueError,
                       match=re.escape(f"{err_str1} ['another', 'bad * result'] {err_str2}")):
        ldr.importer._obj.user_api.extension = ['another', 'bad * result']

    # Check that selected is still/reverted successfully to []
    assert selection_obj.selected == []

    # This should get set to True automatically when multiple selections are made
    selection_obj.multiselect = False
    ldr.importer._obj.user_api.extension = '*'
    assert selection_obj.selected == selection_obj.choices
    assert selection_obj.multiselect is True


def test_viewer_create_new(deconfigged_helper, spectrum1d):
    assert len(deconfigged_helper.new_viewers.keys()) == 0
    # passing [] should not load into a new viewer nor should it create a new viewer
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', viewer=[], data_label='data1')
    assert len(deconfigged_helper.app.data_collection) == 1
    assert len(deconfigged_helper.viewers) == 0
    assert len(deconfigged_helper.new_viewers.keys()) > 0

    # passing nothing when there are no viewers should create a new viewer
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='data2')
    assert len(deconfigged_helper.app.data_collection) == 2
    assert len(deconfigged_helper.viewers) == 1
    assert len(deconfigged_helper.viewers['1D Spectrum'].data_menu.layer.choices) == 1

    # passing nothing when there is a viewer should default to loading into that viewer
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='data3')
    assert len(deconfigged_helper.app.data_collection) == 3
    assert len(deconfigged_helper.viewers) == 1
    assert len(deconfigged_helper.viewers['1D Spectrum'].data_menu.layer.choices) == 2

    # passing a string of a viewer that does not exist should create a viewer with that label
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', viewer='user-defined-viewer', data_label='data4')  # noqa
    assert len(deconfigged_helper.app.data_collection) == 4
    assert len(deconfigged_helper.viewers) == 2
    assert len(deconfigged_helper.viewers['1D Spectrum'].data_menu.layer.choices) == 2
    assert len(deconfigged_helper.viewers['user-defined-viewer'].data_menu.layer.choices) == 1


@pytest.mark.parametrize(
    ("selection", "matches"), [
        ('*', (0, 1, 2, 3)),
        (('*', '*:*'), (0, 1, 2, 3)),
        ('1:*', (0,)),
        ('*S*', (0, 1)),
        (('*ERR*', '*DQ*'), (2, 3)),
        # Brackets should be sanitized, if not this will fail
        ('?: [SCI,1]', (0,)),
        ('?:*', (0, 1, 2, 3)),
    ])
def test_wildcard_match_through_load(imviz_helper, multi_extension_image_hdu_wcs,
                                     selection, matches):
    data_labels = ['Image[SCI,1]',
                   'Image[MASK,1]',
                   'Image[ERR,1]',
                   'Image[DQ,1]']

    # Through load
    imviz_helper.load(multi_extension_image_hdu_wcs, extension=selection)
    assert list(imviz_helper.datasets.keys()) == [data_labels[i] for i in matches]


def test_expected_data_api_class(deconfigged_helper,
                                 image_hdu_wcs, spectrum1d, spectrum2d,
                                 spectrum1d_cube, sky_coord_only_source_catalog):
    """Test that expected DataApi classes are returned for different data types."""
    test_cases = [
        (image_hdu_wcs, 'Image', SpatialDataApi),
        (spectrum1d, '1D Spectrum', SpectralDataApi),
        (spectrum2d, '2D Spectrum', SpectralDataApi),
        (spectrum1d_cube, '3D Spectrum', SpectralSpatialDataApi),
        (sky_coord_only_source_catalog, 'Catalog', DataApi)
    ]

    # Disable linking to speed up test
    deconfigged_helper.app.auto_link = False

    # Load all data at once
    for data, data_format, expected_api in test_cases:
        deconfigged_helper.load(data, format=data_format, data_label=data_format)

    # Check each dataset has the correct API type
    data_dict = deconfigged_helper.datasets
    for data, data_format, expected_api in test_cases:
        msg = (f'Expected {expected_api.__name__} for {data_format}, '
               f'got {type(data_dict[data_format]).__name__}')
        assert isinstance(data_dict[data_format], expected_api), msg

        if f'{data_format} (auto-ext)' in data_dict:
            auto_ext_key = f'{data_format} (auto-ext)'
            msg = (f'Expected SpectralDataApi for {auto_ext_key}, '
                   f'got {type(data_dict[auto_ext_key]).__name__}')
            assert isinstance(data_dict[auto_ext_key], SpectralDataApi), msg


def test_data_access_deconfigged(deconfigged_helper, mos_spectrum2d):
    """Test the .datasets property access for the deconfigged helper."""
    # Initially no data loaded
    assert deconfigged_helper.datasets == {}

    # Load data
    deconfigged_helper.load(mos_spectrum2d, data_label='Test 2D Spectrum',
                            format='2D Spectrum', auto_extract=True)

    # Test datasets property returns dict of DataApi objects
    data_dict = deconfigged_helper.datasets
    assert isinstance(data_dict, dict)
    assert 'Test 2D Spectrum' in data_dict
    assert 'Test 2D Spectrum (auto-ext)' in data_dict
    assert len(data_dict) == 2

    # Test DataApi.get_data() returns Spectrum
    spectrum_obj = data_dict['Test 2D Spectrum'].get_data()
    assert isinstance(spectrum_obj, Spectrum)

    # Test that SpectralDataApi accepts spectral_subset argument (even if None)
    spectrum_no_subset = data_dict['Test 2D Spectrum (auto-ext)'].get_data(spectral_subset=None)
    assert isinstance(spectrum_no_subset, Spectrum)

    # Test add_to_viewer method
    # Get current viewer references
    viewer_1d = deconfigged_helper.viewers['1D Spectrum']

    # Remove data from viewer to test add_to_viewer
    viewer_1d.data_menu.layer = 'Test 2D Spectrum (auto-ext)'
    viewer_1d.data_menu.remove_from_viewer()
    assert 'Test 2D Spectrum (auto-ext)' not in viewer_1d.data_menu.layer.choices
    data_dict['Test 2D Spectrum (auto-ext)'].add_to_viewer('1D Spectrum')
    assert 'Test 2D Spectrum (auto-ext)' in viewer_1d.data_menu.layer.choices

    # Test add_to_viewer with invalid data for viewer raises error
    with pytest.raises(ValueError, match="not one of the valid data"):
        data_dict['Test 2D Spectrum'].add_to_viewer('1D Spectrum')
