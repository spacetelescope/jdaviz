import os

from traitlets import Bool, Float, Unicode, observe

from jdaviz.core.events import AddDataMessage
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from ..events import ChangeSliderMessage

__all__ = ['UnifiedSlider']


@tool_registry('g-unified-slider')
class UnifiedSlider(TemplateMixin):
    template = load_template("unified_slider.vue", __file__).tag(sync=True)
    slider = Float().tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Listen for add data events. **Note** this should only be used in
        #  cases where there is a specific type of data expected and arbitrary
        #  viewers are not expected to be created. That is, the expected data
        #  in _all_ viewers should be uniform.
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)

    def _on_data_added(self, msg):
        if len(msg.data.shape) == 3:
            self.max_value = msg.data.shape[0]

    def vue_on_slider_updated(self, value):
        change_slider_message = ChangeSliderMessage(
            value, sender=self)
        self.hub.broadcast(change_slider_message)
