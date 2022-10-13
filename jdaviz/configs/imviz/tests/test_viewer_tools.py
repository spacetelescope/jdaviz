from numpy.testing import assert_allclose

from jdaviz.configs.imviz.helper import get_top_layer_index
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestContrastBiasTool(BaseImviz_WCS_NoWCS):

    def teardown_method(self, method):
        self.cb_tool.deactivate()

    def test_contrast_bias_mousedrag(self):
        # setup_class is already called by parent class, so we do this here.
        self.cb_tool = self.viewer.toolbar.tools['jdaviz:contrastbias']
        self.cb_tool.activate()

        state = self.viewer.layers[get_top_layer_index(self.viewer)].state

        # Should start with default values.
        assert_allclose(state.bias, 0.5)
        assert_allclose(state.contrast, 1)

        # Simulate some mouse-drag events.

        self.cb_tool.on_mouse_or_key_event({'event': 'dragstart'})

        self.cb_tool.on_mouse_or_key_event({'event': 'dragmove', 'pixel': {'x': 0, 'y': 0}})
        assert_allclose(state.bias, 0)
        assert_allclose(state.contrast, 4)

        self.cb_tool.on_mouse_or_key_event({'event': 'dragmove', 'pixel': {'x': 50, 'y': 50}})
        assert_allclose(state.bias, 0.5050505050505051)
        assert_allclose(state.contrast, 1.9797979797979797)

        self.cb_tool.on_mouse_or_key_event({'event': 'dragmove', 'pixel': {'x': 99, 'y': 99}})
        assert_allclose(state.bias, 1)
        assert_allclose(state.contrast, 0)

        # Out-of-bounds event is ignored.
        self.cb_tool.on_mouse_or_key_event({'event': 'dragmove', 'pixel': {'x': -1, 'y': 50}})
        assert_allclose(state.bias, 1)
        assert_allclose(state.contrast, 0)

        # Simulate double-click reset event.

        self.cb_tool.on_mouse_or_key_event({'event': 'dblclick'})
        assert_allclose(state.bias, 0.5)
        assert_allclose(state.contrast, 1)
