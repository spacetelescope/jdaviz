import numpy as np
import re
from traitlets import Bool, Float, observe, Any, Int

from jdaviz.core.events import AddDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView

__all__ = ['Slice']


@tray_registry('cubeviz-slice', label="Slice")
class Slice(TemplateMixin):
    template_file = __file__, "slice.vue"
    slider = Any(0).tag(sync=True)
    wavelength = Any(0).tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)
    linked = Bool(True).tag(sync=True)
    wait = Int(100).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []
        self._indicator_viewers = []
        self._x_all = None

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

        elif isinstance(msg.viewer, BqplotProfileView):
            if msg.viewer not in self._indicator_viewers:
                self._indicator_viewers.append(msg.viewer)
                # cache wavelengths so that wavelength <> slice conversion can be done efficiently
                # TODO: can this ever be updated?  Possibly with a unit conversion?
                self._x_all = msg.viewer.data()[0].spectral_axis.value
                if self.wavelength == 0.0:
                    self.wavelength = self._x_all[0]
                    self.wavelength_step = self._x_all[1] - self._x_all[0]

    def _slider_value_updated(self, value):
        if len(value) > 0:
            self.slider = float(value[0])

    def vue_change_wavelength(self, event):
        # convert to float after stripping any invalid characters
        value = float(re.sub(r'[^-+eE\d.]', '', event))

        # NOTE: by setting the index, this should recursively update the
        # wavelength to the nearest applicable value in _on_slider_updated
        self.slider = int(np.argmin(abs(value - self._x_all)))

    @observe('slider')
    def _on_slider_updated(self, event):
        if not event['new']:
            value = 0
        else:
            value = int(event['new'])

        self.wavelength = self._x_all[value]

        if self.linked:
            for viewer in self._watched_viewers:
                viewer.state.slices = (value, 0, 0)
            for viewer in self._indicator_viewers:
                viewer._update_slice_indicator(value)
