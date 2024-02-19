import threading
import time
import warnings

import numpy as np
import astropy.units as u
from astropy.units import UnitsWarning
from astropy.utils.decorators import deprecated
from traitlets import Any, Bool, Float, Int, Unicode, observe

from jdaviz.configs.cubeviz.plugins.viewers import (WithSliceIndicator, WithSliceSelection,
                                                    CubevizImageView)
from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import (AddDataMessage, SliceToolStateMessage,
                                SliceSelectSliceMessage, SliceValueUpdatedMessage,
                                NewViewerMessage, ViewerAddedMessage, ViewerRemovedMessage,
                                GlobalDisplayUnitChanged)
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
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``value``
      Value (wavelength or frequency) of the current slice.  When setting this directly, it will
      update automatically to the value corresponding to the nearest slice.
    * ``snap_to_slice``
      Whether the indicator should snap to the value of the nearest slice in the cube.
    * ``show_indicator``
      Whether to show indicator in spectral viewer when slice tool is inactive.
    * ``show_value``
      Whether to show slice value in label to right of indicator.
    """
    _cube_viewer_cls = CubevizImageView
    _cube_viewer_default_label = 'flux-viewer'
    cube_viewer_exists = Bool(True).tag(sync=True)

    template_file = __file__, "slice.vue"
    value = FloatHandleEmpty().tag(sync=True)
    value_label = Unicode("Wavelength").tag(sync=True)
    value_unit = Unicode("").tag(sync=True)

    slider_throttle = Int(200).tag(sync=True)  # milliseconds

    snap_to_slice = Bool(True).tag(sync=True)
    show_indicator = Bool(True).tag(sync=True)
    show_value = Bool(True).tag(sync=True)

    is_playing = Bool(False).tag(sync=True)
    play_interval = Int(200).tag(sync=True)  # milliseconds

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._player = None

        # Subscribe to requests from the helper to change the slice across all viewers
        self.session.hub.subscribe(self, SliceSelectSliceMessage,
                                   handler=self._on_select_slice_message)

        # Listen for new viewers.
        self.session.hub.subscribe(self, ViewerAddedMessage,
                                   handler=self._on_viewer_added)
        self.session.hub.subscribe(self, ViewerRemovedMessage,
                                   handler=self._on_viewer_removed)
        # connect any pre-existing viewers
        for viewer in self.app._viewer_store.values():
            self._connect_viewer(viewer)
        # initialize if cube viewer exists
        self._check_if_cube_viewer_exists()

        # update internal value (wavelength/frequency) when x display unit is changed
        # so that the current slice number is preserved
        self.session.hub.subscribe(self, GlobalDisplayUnitChanged,
                                   handler=self._on_global_display_unit_changed)

    @property
    def slice_axis(self):
        # global display unit "axis" corresponding to the slice axis
        return 'spectral'

    @property
    def slice_selection_viewers(self):
        return [v for v in self.app._viewer_store.values() if isinstance(v, WithSliceSelection)]

    @property
    def slice_indicator_viewers(self):
        return [v for v in self.app._viewer_store.values() if isinstance(v, WithSliceIndicator)]

    @property
    @deprecated(since="3.9", alternative="value")
    def wavelength(self):
        return self.user_api.value

    @property
    @deprecated(since="3.9", alternative="value_unit")
    def wavelength_unit(self):
        return self.user_api.value_unit

    @property
    @deprecated(since="3.9", alternative="show_value")
    def show_wavelength(self):
        return self.user_api.show_value

    @property
    @deprecated(since="3.9", alternative="value")
    def slice(self):
        return self.slice_selection_viewers[0].slice

    @property
    def user_api(self):
        # NOTE: remove slice, wavelength, show_wavelength after deprecation period
        return PluginUserApi(self, expose=('slice', 'wavelength', 'show_wavelength',
                                           'value',
                                           'snap_to_slice', 'show_indicator', 'show_value'))

    def _check_if_cube_viewer_exists(self, *args):
        for viewer in self.app._viewer_store.values():
            if isinstance(viewer, self._cube_viewer_cls):
                self.cube_viewer_exists = True
                return
        self.cube_viewer_exists = False

    def vue_create_cube_viewer(self, *args):
        self.app._on_new_viewer(NewViewerMessage(self._cube_viewer_cls, data=None, sender=self.app),
                                vid=self._cube_viewer_default_label,
                                name=self._cube_viewer_default_label)

        dc = self.app.data_collection
        for data in dc:
            if data.ndim == 3:
                # only load the first cube-like data
                self.app.set_data_visibility(self._cube_viewer_default_label, data.label, True)
                break

    def _connect_viewer(self, viewer):
        if isinstance(viewer, WithSliceSelection):
            # instead of just setting viewer.slice_value, we'll make sure the "snapping" logic
            # is updated (if enabled)
            self._on_value_updated({'new': self.value})

        if isinstance(viewer, WithSliceIndicator):
            # NOTE: on first call, this will initialize the indicator itself
            viewer._set_slice_indicator_value(self.value)

    def _on_viewer_added(self, msg):
        viewer = self.app.get_viewer(msg.viewer_id)
        self._connect_viewer(viewer)
        self._check_if_cube_viewer_exists()

    def _on_viewer_removed(self, msg):
        self._check_if_cube_viewer_exists()

    def _on_select_slice_message(self, msg):
        # NOTE: by setting the slice index, the observer (_on_slider_updated)
        # will sync across all viewers and update the value (wavelength/frequency)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UnitsWarning)
            self.value = msg.value

    def _on_global_display_unit_changed(self, msg):
        if msg.axis != self.slice_axis:
            return
        prev_unit = self.value_unit
        # TODO: update self.value and self.value_unit and ensure that updates all indicator labels

    @observe('value')
    def _on_value_updated(self, event):
        # convert to float (JS handles stripping any invalid characters)
        try:
            value = float(event.get('new'))
        except ValueError:
            # TODO: do we need to revert?
            return

        if self.snap_to_slice and len(self.slice_selection_viewers):
            valid_values = np.concatenate([viewer.slice_values for viewer in self.slice_selection_viewers])
            if len(valid_values):
                closest_ind = np.argmin(abs(valid_values - value))
                closest_value = valid_values[closest_ind]
                if self.value != closest_value:
                    self.value = closest_value
                    # will trigger another call to this method
                    return

        for viewer in self.slice_indicator_viewers:
            viewer._set_slice_indicator_value(value)
        for viewer in self.slice_selection_viewers:
            # TODO: map value > slice either here or in the following method
            viewer.slice_value = value

        self.hub.broadcast(SliceValueUpdatedMessage(value=self.value,
                                                    value_unit=self.value_unit,
                                                    sender=self))

    @observe('snap_to_slice')
    def _on_snap_to_slice_changed(self, event):
        if self.snap_to_slice:
            self._on_value_updated({'new': self.value})

    @observe('show_indicator', 'show_value')
    def _on_setting_changed(self, event):
        msg = SliceToolStateMessage({event['name']: event['new']}, viewer=None, sender=self)
        self.session.hub.broadcast(msg)

    def vue_goto_first(self, *args):
        if self.is_playing:
            return
        self._on_slider_updated({'new': self.min_slice})

    def vue_goto_last(self, *args):
        if self.is_playing:
            return
        self._on_slider_updated({'new': self.max_slice})

    def vue_play_next(self, *args):
        if self.is_playing:
            return
        # TODO: update to not rely on self.slice
        self._on_slider_updated({'new': self.slice + 1})

    def _player_worker(self):
        ts = float(self.play_interval) * 1e-3  # ms to s
        while self.is_playing:
            # TODO: update to not rely on self.slice
            self._on_slider_updated({'new': self.slice + 1})
            time.sleep(ts)

    def vue_play_start_stop(self, *args):
        if self.is_playing:  # Stop
            if self._player:
                if self._player.is_alive():
                    self._player.join(timeout=0)
                self._player = None
            self.is_playing = False
            return

        if len(self.slice_indicator_viewers) == 0 and len(self.slice_selection_viewers) == 0:
            return

        # Start
        self.is_playing = True
        self._player = threading.Thread(target=self._player_worker)
        self._player.start()
