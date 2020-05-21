from traitlets import Bool, Float, observe, Any

from jdaviz.core.events import AddDataMessage
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from glue_jupyter.bqplot.image import BqplotImageView

__all__ = ['UnifiedSlider']


@tool_registry('g-unified-slider')
class UnifiedSlider(TemplateMixin):
    template = load_template("unified_slider.vue", __file__).tag(sync=True)
    slider = Any(0).tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)
    linked = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []

        # Listen for add data events. **Note** this should only be used in
        #  cases where there is a specific type of data expected and arbitrary
        #  viewers are not expected to be created. That is, the expected data
        #  in _all_ viewers should be uniform.
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)

    @observe("linked")
    def _on_linked_changed(self, event):
        for viewer in self._watched_viewers:

            if not event['new']:
                viewer.state.remove_callback('slices',
                                             self._slider_value_updated)
            else:
                viewer.state.add_callback('slices',
                                          self._slider_value_updated)

    def _on_data_added(self, msg):
        if len(msg.data.shape) == 3 and \
                isinstance(msg.viewer, BqplotImageView):
            self.max_value = msg.data.shape[0] - 1

            if msg.viewer not in self._watched_viewers:
                self._watched_viewers.append(msg.viewer)

                msg.viewer.state.add_callback('slices',
                                              self._slider_value_updated)

    def _slider_value_updated(self, value):
        if len(value) > 0:
            self.slider = float(value[0])

    @observe('slider')
    def _on_slider_updated(self, event):
        if not event['new']:
            value = 0
        else:
            value = int(event['new'])

        if self.linked:
            for viewer in self._watched_viewers:
                viewer.state.slices = (value, 0, 0)
