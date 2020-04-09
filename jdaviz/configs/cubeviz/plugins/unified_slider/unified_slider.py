import os

from traitlets import Bool, Float, Unicode, observe

from jdaviz.core.events import AddDataMessage, AddViewerMessage
from jdaviz.core.registries import tool_registry, viewer_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from glue.external.echo import add_callback, remove_callback, delay_callback
from glue_jupyter.bqplot.image import BqplotImageView

__all__ = ['UnifiedSlider']


@tool_registry('g-unified-slider')
class UnifiedSlider(TemplateMixin):
    template = load_template("unified_slider.vue", __file__).tag(sync=True)
    slider = Float().tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []

        # Listen for add data events. **Note** this should only be used in
        #  cases where there is a specific type of data expected and arbitrary
        #  viewers are not expected to be created. That is, the expected data
        #  in _all_ viewers should be uniform.
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)

    def _on_data_added(self, msg):
        if len(msg.data.shape) == 3 and \
                isinstance(msg.viewer, BqplotImageView):
            self.max_value = msg.data.shape[0]

            self._watched_viewers.append(msg.viewer)

            # remove_callback(self._watched_viewer.state, 'slices',
            #                 self._slider_value_updated)

            add_callback(msg.viewer.state, 'slices',
                         self._slider_value_updated)

    def _slider_value_updated(self, value):
        self.slider = value[0]

    @observe('slider')
    def _on_slider_updated(self, event):
        for viewer in self._watched_viewers:
            viewer.state.slices = (event['new'], 0, 0)
