import numpy as np
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from traitlets import Bool, Float, observe, Any, Int
from specutils.spectra.spectrum1d import Spectrum1D

from jdaviz.core.events import AddDataMessage, SliceToolStateMessage, SliceSelectSliceMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['Slice']


@tray_registry('cubeviz-slice', label="Slice")
class Slice(TemplateMixin):
    template_file = __file__, "slice.vue"
    slider = Any(0).tag(sync=True)
    wavelength = Any(-1).tag(sync=True)
    wavelength_unit = Any("").tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)
    linked = Bool(True).tag(sync=True)
    wait = Int(200).tag(sync=True)

    setting_show_indicator = Bool(True).tag(sync=True)
    setting_show_wavelength = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._watched_viewers = []
        self._indicator_viewers = []
        self._x_all = None

        # Subscribe to requests from the helper to change the slice across all viewers
        self.session.hub.subscribe(self, SliceSelectSliceMessage,
                                   handler=self._on_select_slice_message)

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
                                             self._viewer_slices_changed)
            else:
                viewer.state.add_callback('slices',
                                          self._viewer_slices_changed)

    def _on_data_added(self, msg):
        if len(msg.data.shape) == 3 and isinstance(msg.viewer, BqplotImageView):
            self.max_value = msg.data.shape[0] - 1

            if msg.viewer not in self._watched_viewers:
                self._watched_viewers.append(msg.viewer)

                msg.viewer.state.add_callback('slices',
                                              self._viewer_slices_changed)

        elif isinstance(msg.viewer, BqplotProfileView):
            if msg.viewer not in self._indicator_viewers:
                self._indicator_viewers.append(msg.viewer)
                # cache wavelengths so that wavelength <> slice conversion can be done efficiently
                x_all = msg.viewer.data()[0].spectral_axis
                self._x_all = x_all.value
                self.wavelength_unit = str(x_all.unit)
                # but if the units (or data) change, we need to update internally
                msg.viewer.state.add_callback("reference_data",
                                              self._update_reference_data)

                if self.wavelength == -1:
                    # initialize at middle of cube
                    self.slider = int(len(x_all)/2)

    def _update_reference_data(self, reference_data):
        if reference_data is None:
            return
        self._update_data(reference_data.get_object(cls=Spectrum1D).spectral_axis)

    def _update_data(self, x_all):
        if hasattr(x_all, 'unit'):
            self.wavelength_unit = str(x_all.unit)
            x_all = x_all.value

        self._x_all = x_all
        # force wavelength to update from the current slider value
        self._on_slider_updated({'new': self.slider})

    def _viewer_slices_changed(self, value):
        # the slices attribute on the viewer state was changed,
        # so we'll update the slider to match which will trigger
        # the slider observer (_on_slider_updated) and sync across
        # any other applicable viewers
        if len(value):
            self.slider = float(value[0])

    def _on_select_slice_message(self, msg):
        # NOTE: by setting the slice index, the observer (_on_slider_updated)
        # will sync across all viewers and update the wavelength
        self.slider = msg.slice

    def vue_change_wavelength(self, event):
        # convert to float after stripping any invalid characters
        try:
            value = float(event)
        except ValueError:
            # do not accept changes, we'll revert via the slider
            # since this @change event doesn't have access to
            # the old value, and self.wavelength already updated
            # via the v-model
            self._on_slider_updated({'new': self.slider})
            return

        # NOTE: by setting the index, this should recursively update the
        # wavelength to the nearest applicable value in _on_slider_updated
        self.slider = int(np.argmin(abs(value - self._x_all)))

    @observe('setting_show_indicator', 'setting_show_wavelength')
    def _on_setting_changed(self, event):
        msg = SliceToolStateMessage({event['name']: event['new']}, sender=self)
        self.session.hub.broadcast(msg)

    @observe('slider')
    def _on_slider_updated(self, event):
        value = int(event.get('new', 0))

        self.wavelength = self._x_all[value]

        if self.linked:
            for viewer in self._watched_viewers:
                viewer.state.slices = (value, 0, 0)
            for viewer in self._indicator_viewers:
                viewer._update_slice_indicator(value)
