import warnings

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
    ldr = imviz_helper.loaders['object']
    ldr.object = multi_extension_image_hdu_wcs
    extension_obj = ldr.importer.extension

    # Leaving this here for future reference
    assert extension_obj.choices == ['1: [SCI,1]',
                                     '2: [MASK,1]',
                                     '3: [ERR,1]',
                                     '4: [DQ,1]']

    extension_obj.multiselect = False

    # Test all
    ldr.importer._obj.user_api.extension = '*'
    assert extension_obj.multiselect is True
    assert extension_obj.selected == extension_obj.choices

    extension_obj.multiselect = False
    # Test for repeats
    ldr.importer._obj.user_api.extension = ['*', '*:*']
    assert extension_obj.multiselect is True
    assert extension_obj.selected == extension_obj.choices

    # Resetting
    extension_obj.selected = []
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

    ldr.importer._obj.user_api.extension = '1:*'
    assert extension_obj.selected == [extension_obj.choices[0]]

    ldr.importer._obj.user_api.extension = '*S*'
    assert extension_obj.selected == extension_obj.choices[:2]

    ldr.importer._obj.user_api.extension = ['*ERR*', '*DQ*']
    assert extension_obj.selected == extension_obj.choices[2:]
