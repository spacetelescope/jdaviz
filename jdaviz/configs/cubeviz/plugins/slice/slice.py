import warnings
from astropy.units import UnitsWarning
import numpy as np
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from traitlets import Bool, Float, observe, Any, Int
from specutils.spectra.spectrum1d import Spectrum1D

from jdaviz.core.events import AddDataMessage, SliceToolStateMessage, SliceSelectSliceMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Slice']


@tray_registry('cubeviz-slice', label="Slice", viewer_requirements='spectrum')
class Slice(PluginTemplateMixin):
    """
    See the :ref:`Slice Plugin Documentation <slice>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``slice``
      Current slice number.
    * ``wavelength``
      Wavelength of the current slice.  When setting this directly, it will update automatically to
      the wavelength corresponding to the nearest slice.
    * ``show_indicator``
      Whether to show indicator in spectral viewer when slice tool is inactive.
    * ``show_wavelength``
      Whether to show slice wavelength in label to right of indicator.
    """
    template_file = __file__, "slice.vue"
    slice = Any(0).tag(sync=True)
    wavelength = Any(-1).tag(sync=True)
    wavelength_unit = Any("").tag(sync=True)
    min_value = Float(0).tag(sync=True)
    max_value = Float(100).tag(sync=True)
    wait = Int(200).tag(sync=True)

    show_indicator = Bool(True).tag(sync=True)
    show_wavelength = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._default_image_viewer_reference_name = kwargs.get(
            "image_viewer_reference_name", "image-viewer"
        )
        super().__init__(*args, **kwargs)

        self._watched_viewers = []
        self._indicator_viewers = []
        self._x_all = None

        # initialize watching existing viewers WITH data (if initializing the plugin after data
        # already exists - otherwise the AddDataMessage will handle watching image viewers once
        # data is available)
        for id, viewer in self.app._viewer_store.items():
            if isinstance(viewer, BqplotProfileView) or len(viewer.data()):
                self._watch_viewer(viewer, True)

        # Subscribe to requests from the helper to change the slice across all viewers
        self.session.hub.subscribe(self, SliceSelectSliceMessage,
                                   handler=self._on_select_slice_message)

        # Listen for add data events. **Note** this should only be used in
        #  cases where there is a specific type of data expected and arbitrary
        #  viewers are not expected to be created. That is, the expected data
        #  in _all_ viewers should be uniform.
        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_data_added)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('slice', 'wavelength',
                                           'show_indicator', 'show_wavelength'))

    def _watch_viewer(self, viewer, watch=True):
        if isinstance(viewer, BqplotImageView):
            if watch and viewer not in self._watched_viewers:
                self._watched_viewers.append(viewer)
                viewer.state.add_callback('slices',
                                          self._viewer_slices_changed)
            elif not watch and viewer in self._watched_viewers:
                viewer.state.remove_callback('slices',
                                             self._viewer_slices_changed)
                self._watched_viewers.remove(viewer)
        elif isinstance(viewer, BqplotProfileView) and watch:
            if self._x_all is None and len(viewer.data()):
                # cache wavelengths so that wavelength <> slice conversion can be done efficiently
                self._update_data(viewer.data()[0].spectral_axis)

            if viewer not in self._indicator_viewers:
                self._indicator_viewers.append(viewer)
                # if the units (or data) change, we need to update internally
                viewer.state.add_callback("reference_data",
                                          self._update_reference_data)

    def _on_data_added(self, msg):
        if isinstance(msg.viewer, BqplotImageView):
            if len(msg.data.shape) == 3:
                self.max_value = msg.data.shape[-1] - 1
                self._watch_viewer(msg.viewer, True)

        elif isinstance(msg.viewer, BqplotProfileView):
            self._watch_viewer(msg.viewer, True)

    def _update_reference_data(self, reference_data):
        if reference_data is None:
            return  # pragma: no cover
        self._update_data(reference_data.get_object(cls=Spectrum1D).spectral_axis)

    def _update_data(self, x_all):
        if hasattr(x_all, 'unit'):
            self.wavelength_unit = str(x_all.unit)
            x_all = x_all.value

        self._x_all = x_all

        if self.wavelength == -1:
            if len(x_all):
                # initialize at middle of cube
                self.slice = int(len(x_all)/2)
            else:
                # leave in the pre-init state and don't update the wavelength/slice
                return

        # force wavelength to update from the current slider value
        self._on_slider_updated({'new': self.slice})

    def _viewer_slices_changed(self, value):
        # the slices attribute on the viewer state was changed,
        # so we'll update the slider to match which will trigger
        # the slider observer (_on_slider_updated) and sync across
        # any other applicable viewers
        if len(value) == 3:
            self.slice = float(value[-1])

    def _on_select_slice_message(self, msg):
        # NOTE: by setting the slice index, the observer (_on_slider_updated)
        # will sync across all viewers and update the wavelength
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UnitsWarning)
            self.slice = msg.slice

    @observe('wavelength')
    def _on_wavelength_updated(self, event):
        # convert to float (JS handles stripping any invalid characters)
        try:
            value = float(event.get('new'))
        except ValueError:
            # do not accept changes, we'll revert via the slider
            # since this @change event doesn't have access to
            # the old value, and self.wavelength already updated
            # via the v-model
            self._on_slider_updated({'new': self.slice})
            return

        # NOTE: by setting the index, this should recursively update the
        # wavelength to the nearest applicable value in _on_slider_updated
        self.slice = int(np.argmin(abs(value - self._x_all)))

    @observe('show_indicator', 'show_wavelength')
    def _on_setting_changed(self, event):
        msg = SliceToolStateMessage({event['name']: event['new']}, sender=self)
        self.session.hub.broadcast(msg)

    @observe('slice')
    def _on_slider_updated(self, event):
        value = int(event.get('new', int(len(self._x_all)/2)))

        self.wavelength = self._x_all[value]

        for viewer in self._watched_viewers:
            viewer.state.slices = (0, 0, value)
        for viewer in self._indicator_viewers:
            viewer._update_slice_indicator(value)
