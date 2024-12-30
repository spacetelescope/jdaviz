from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


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
    assert specviz_helper.viewers['spectrum-viewer'].data_labels_loaded == [label]
    assert specviz_helper.viewers['spectrum-viewer'].data_labels_visible == [label]


def test_toggle_api_hints(specviz_helper):
    assert specviz_helper.app.state.show_api_hints is False
    specviz_helper.toggle_api_hints()
    assert specviz_helper.app.state.show_api_hints is True
    specviz_helper.toggle_api_hints(True)
    assert specviz_helper.app.state.show_api_hints is True
    specviz_helper.toggle_api_hints()
    assert specviz_helper.app.state.show_api_hints is False
