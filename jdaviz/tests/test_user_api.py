from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
import pytest
import re


# This applies to all viz but testing with Imviz should be enough.
class TestImviz_WCS_WCS(BaseImviz_WCS_WCS):
    def test_imviz_zoom_level(self):
        v = self.imviz.viewers['imviz-0']
        assert v._obj.state.x_min == -0.5
        assert v._obj.state.x_max == 9.5

        v.zoom(2)

        assert v._obj.state.x_min == 1.5
        assert v._obj.state.x_max == 6.5

    def test_imviz_viewers(self):
        self.imviz.create_image_viewer()
        self.imviz.create_image_viewer()

        # regression test for https://github.com/spacetelescope/jdaviz/pull/2624
        assert len(self.imviz.viewers) == 3


def test_specviz_zoom_level(specviz_helper):
    v = specviz_helper.viewers['spectrum-viewer']
    v.set_limits(x_min=1, x_max=2, y_min=1, y_max=2)
    assert v._obj.state.x_min == 1
    assert v._obj.state.x_max == 2
    assert v._obj.state.y_min == 1
    assert v._obj.state.y_max == 2


def test_specviz_data_labels(specviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_helper.load_data(spectrum1d, data_label=label)

    assert specviz_helper.data_labels == [label]
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


def test_wildcard_matching(imviz_helper, multi_extension_image_hdu_wcs):
    default_choices = ['1: [SCI,1]',
                       '2: [MASK,1]',
                       '3: [ERR,1]',
                       '4: [DQ,1]']

    # Testing directly
    ldr = imviz_helper.loaders['object']
    ldr.object = multi_extension_image_hdu_wcs
    extension_obj = ldr.importer.extension
    # Default selection
    assert extension_obj.selected == [default_choices[0]]
    # Resetting to []
    # Note this can't be done by setting selected = [], is this intentional?
    extension_obj.selected.pop(0)

    assert extension_obj.choices == default_choices
    extension_obj.multiselect = False

    err_str1 = "not all items in"
    err_str2 = f"are one of {extension_obj.choices}, reverting selection to []"
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
    assert extension_obj.selected == []

    test_selections = {
        # Test all
        '*': extension_obj.choices,
        # Test repeats
        ('*', '*:*'): extension_obj.choices,
        # Test single selection
        '1:*': [extension_obj.choices[0]],
        # Test multi-wildcard
        '*S*': extension_obj.choices[:2],
        # Test multi-selection
        ('*ERR*', '*DQ*'): extension_obj.choices[2:]}

    # Check both direct and through load
    for selection, expected in test_selections.items():
        # Direct
        ldr.importer._obj.user_api.extension = selection
        assert extension_obj.multiselect is True
        assert extension_obj.selected == expected
        # Reset
        extension_obj.selected = []

        # Through load
        imviz_helper.load(multi_extension_image_hdu_wcs, extension=selection)
        #print(imviz_helper.app.data_collection.labels)# == expected
        #raise Exception()

        # Reset
        extension_obj.selected = []
