import threading
import time
import warnings

import numpy as np
from astropy import units as u
from astropy.units import UnitsWarning
from astropy.utils.decorators import deprecated
from traitlets import Bool, Int, Unicode, observe

from jdaviz.configs.cubeviz.plugins.viewers import (WithSliceIndicator, WithSliceSelection,
                                                    CubevizImageView)
from jdaviz.configs.cubeviz.helper import _spectral_axis_names
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
      update automatically to the value corresponding to the nearest slice, if ``snap_to_slice`` is
      enabled.
    * ``show_indicator``
      Whether to show indicator in spectral viewer when slice tool is inactive.
    * ``show_value``
      Whether to show slice value in label to right of indicator.
    """
    _cube_viewer_cls = CubevizImageView
    _cube_viewer_default_label = 'flux-viewer'
    cube_viewer_exists = Bool(True).tag(sync=True)

    allow_disable_snapping = Bool(False).tag(sync=True)  # noqa internal use to show and allow disabling snap-to-slice

    template_file = __file__, "slice.vue"
    value = FloatHandleEmpty().tag(sync=True)
    value_label = Unicode("Value").tag(sync=True)
    value_unit = Unicode("").tag(sync=True)
    value_editing = Bool(False).tag(sync=True)  # whether the value input is actively being edited

    slider_throttle = Int(200).tag(sync=True)  # milliseconds

    snap_to_slice = Bool(True).tag(sync=True)
    show_indicator = Bool(True).tag(sync=True)
    show_value = Bool(True).tag(sync=True)

    is_playing = Bool(False).tag(sync=True)
    play_interval = Int(200).tag(sync=True)  # milliseconds

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._indicator_initialized = False
        self._player = None

        # Subscribe to requests from the helper to change the slice across all viewers
        self.session.hub.subscribe(self, SliceSelectSliceMessage,
                                   handler=self._on_select_slice_message)

        # Listen for new viewers/data.
        self.session.hub.subscribe(self, ViewerAddedMessage,
                                   handler=self._on_viewer_added)
        self.session.hub.subscribe(self, ViewerRemovedMessage,
                                   handler=self._on_viewer_removed)
        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_add_data)

        # connect any pre-existing viewers
        for viewer in self.app._viewer_store.values():
            self._connect_viewer(viewer)

        # initialize if cube viewer exists
        self._check_if_cube_viewer_exists()

        # update internal value (wavelength/frequency) when x display unit is changed
        # so that the current slice number is preserved
        self.session.hub.subscribe(self, GlobalDisplayUnitChanged,
                                   handler=self._on_global_display_unit_changed)
        self._initialize_location()

    def _initialize_location(self, *args):
        # initialize value_unit (this has to wait until data is loaded to an existing
        # slice_indicator_viewer, so we'll keep trying until it is set - after that, changes
        # will be handled by a change to global display units)
        if not self.value_unit:
            for viewer in self.slice_indicator_viewers:
                # ignore while x_display_unit is unset or still degrees (before data transpose)
                # if we ever need the slice axis to be degrees, this will need to be loosened
                if getattr(viewer.state, 'x_display_unit', None) not in (None, 'deg'):
                    self.value_unit = viewer.state.x_display_unit
                    break

        if self._indicator_initialized:
            return

        # set initial value (and snap to nearest point, if enabled)
        # we'll loop over all slice indicator viewers and their layers
        # and just use the first layer with data.  Once initialized, this logic will be
        # skipped going forward to not change any user selection (so will default to the
        # middle of the first found layer)
        for viewer in self.slice_indicator_viewers:
            if str(viewer.state.x_att) not in self.valid_slice_att_names:
                # avoid setting value to degs, before x_att is changed to wavelength, for example
                continue
            slice_values = viewer.slice_values
            if len(slice_values):
                self.value = slice_values[int(len(slice_values)/2)]
                self._indicator_initialized = True
                return

    @property
    def slice_axis(self):
        # global display unit "axis" corresponding to the slice axis
        return 'spectral'

    @property
    def valid_slice_att_names(self):
        return _spectral_axis_names + ['Pixel Axis 2 [x]']

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
        # this assumes the first slice_selection_viewer (and layer)
        return self.slice_selection_viewers[0].slice

    @slice.setter
    @deprecated(since="3.9", alternative="value")
    def slice(self, slice):
        # this assumes the first slice_selection_viewer (and layer)
        value = self.slice_selection_viewers[0].slice_values[slice]
        self.value = value

    @property
    def user_api(self):
        # NOTE: remove slice, wavelength, show_wavelength after deprecation period
        expose = ['slice', 'wavelength', 'show_wavelength',
                  'value',
                  'show_indicator', 'show_value']
        if self.allow_disable_snapping:
            expose += ['snap_to_slice']
        return PluginUserApi(self, expose=expose)

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
        if isinstance(viewer, WithSliceIndicator):
            # NOTE: on first call, this will initialize the indicator itself
            viewer._set_slice_indicator_value(self.value)
        # in the case where x_att is changed after the viewer is added or data is loaded, we
        # may still need to initialize the location to a valid value (with a valid x_att)
        viewer.state.add_callback('x_att', self._initialize_location)

    def _on_viewer_added(self, msg):
        viewer = self.app.get_viewer(msg.viewer_id)
        self._connect_viewer(viewer)
        self._check_if_cube_viewer_exists()

    def _on_viewer_removed(self, msg):
        self._check_if_cube_viewer_exists()

    def _on_add_data(self, msg):
        self._initialize_location()
        if isinstance(msg.viewer, WithSliceSelection):
            # instead of just setting viewer.slice_value, we'll make sure the "snapping" logic
            # is updated (if enabled)
            self._on_value_updated({'new': self.value})

    def _on_select_slice_message(self, msg):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', category=UnitsWarning)
            self.value = msg.value

    def _on_global_display_unit_changed(self, msg):
        if msg.axis != self.slice_axis:
            return
        if not self.value_unit:
            self.value_unit = str(msg.unit)
            return
        prev_unit = u.Unit(self.value_unit)
        self.value_unit = str(msg.unit)
        self.value = (self.value * prev_unit).to_value(msg.unit)

    @property
    def valid_selection_values(self):
        # all available slice values from cubes (unsorted)
        viewers = self.slice_selection_viewers
        if not len(viewers):
            return np.array([])
        return np.unique(np.concatenate([viewer.slice_values for viewer in viewers]))

    @property
    def valid_selection_values_sorted(self):
        # all available slice values from cubes (sorted)
        return np.sort(self.valid_selection_values)

    @property
    def valid_indicator_values(self):
        # all x-values in indicator viewers (unsorted)
        viewers = self.slice_indicator_viewers
        if not len(viewers):
            return np.array([])
        return np.unique(np.concatenate([viewer.slice_values for viewer in viewers]))

    @property
    def valid_indicator_values_sorted(self):
        return np.sort(self.valid_indicator_values)

    @property
    def valid_values(self):
        return self.valid_selection_values if self.cube_viewer_exists else self.valid_indicator_values  # noqa

    @property
    def valid_values_sorted(self):
        return self.valid_selection_values_sorted if self.cube_viewer_exists else self.valid_indicator_values_sorted  # noqa

    @observe('value')
    def _on_value_updated(self, event):
        # convert to float (JS handles stripping any invalid characters)
        if not isinstance(event.get('new'), float):
            try:
                self.value = float(event.get('new'))
            except ValueError:
                return
            return

        if self.snap_to_slice and not self.value_editing:
            valid_values = self.valid_selection_values
            if len(valid_values):
                closest_ind = np.argmin(abs(valid_values - self.value))
                closest_value = valid_values[closest_ind]
                if self.value != closest_value:
                    # cast to float in case closest_value is an integer (which would otherwise
                    # raise an error with setting to the float traitlet)
                    self.value = float(closest_value)
                    # will trigger another call to this method
                    return

        for viewer in self.slice_indicator_viewers:
            viewer._set_slice_indicator_value(self.value)
        for viewer in self.slice_selection_viewers:
            viewer.slice_value = self.value

        self.hub.broadcast(SliceValueUpdatedMessage(value=self.value,
                                                    value_unit=self.value_unit,
                                                    sender=self))

    @observe('snap_to_slice', 'value_editing')
    def _on_snap_to_slice_changed(self, event):
        if self.snap_to_slice and not self.value_editing:
            self._on_value_updated({'new': self.value})

    @observe('show_indicator', 'show_value')
    def _on_setting_changed(self, event):
        msg = SliceToolStateMessage({event['name']: event['new']}, viewer=None, sender=self)
        self.session.hub.broadcast(msg)

    def vue_goto_first(self, *args):
        if self.is_playing:
            return
        self.value = np.nanmin(self.valid_values)

    def vue_goto_last(self, *args):
        if self.is_playing:
            return
        self.value = np.nanmax(self.valid_values)

    def vue_play_prev(self, *args):
        if self.is_playing:
            return
        valid_values = self.valid_values_sorted
        if not len(valid_values):
            return
        current_ind = np.argmin(abs(valid_values - self.value))
        if current_ind == 0:
            # wrap
            self.value = valid_values[len(valid_values) - 1]
        else:
            self.value = valid_values[current_ind - 1]

    def vue_play_next(self, *args):
        if self.is_playing:
            return
        valid_values = self.valid_values_sorted
        if not len(valid_values):
            return
        current_ind = np.argmin(abs(valid_values - self.value))
        if len(valid_values) <= current_ind + 1:
            # wrap
            self.value = valid_values[0]
        else:
            self.value = valid_values[current_ind + 1]

    def _player_worker(self):
        ts = float(self.play_interval) * 1e-3  # ms to s
        valid_values = self.valid_values_sorted
        if not len(valid_values):
            self.is_playing = False
            return
        while self.is_playing:
            # recompute current_ind in case user has moved slider
            # could optimize this by only recomputing after a select slice message
            # (will only make a difference if argmin becomes approaches play_interval)
            current_ind = np.argmin(abs(valid_values - self.value))
            if len(valid_values) <= current_ind + 1:
                # wrap
                self.value = valid_values[0]
            else:
                self.value = valid_values[current_ind + 1]
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
        if not len(self.valid_values_sorted):
            return

        # Start
        self.is_playing = True
        self._player = threading.Thread(target=self._player_worker)
        self._player.start()
