import numpy as np
import astropy.units as u
from functools import cached_property
from glue.core import BaseData

from glue.core.subset_group import GroupedSubset
from bqplot import Lines
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicatorMarks, ShadowSpatialSpectral
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, GlobalDisplayUnitChanged
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.utils import get_subset_type

__all__ = ['CubevizImageView', 'CubevizProfileView',
           'WithSliceIndicator', 'WithSliceSelection']


class WithSliceIndicator:
    @property
    def slice_component_label(self):
        return str(self.state.x_att)

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @cached_property
    def slice_indicator(self):
        # SliceIndicatorMarks does not yet exist
        slice_indicator = SliceIndicatorMarks(self)
        self.figure.marks = self.figure.marks + slice_indicator.marks
        return slice_indicator

    @cached_property
    def slice_values(self):

        def _get_component(layer):
            # Retrieve display units
            slice_display_units = self.jdaviz_app._get_display_unit(
                self.slice_display_unit_name
            )

            try:
                # Retrieve layer data and units
                data_comp = layer.layer.data.get_component(self.slice_component_label)
            except (AttributeError, KeyError):
                # layer either does not have get_component (because its a subset)
                # or slice_component_label is not a component in this layer
                # either way, return an empty array and skip this layer
                return np.array([])

            # Convert axis if display units are set and are different
            data_units = getattr(data_comp, 'units', None)
            if slice_display_units and data_units and slice_display_units != data_units:
                data = np.asarray(data_comp.data, dtype=float) * u.Unit(data_units)
                return data.to_value(slice_display_units,
                                     equivalencies=u.spectral())
            else:
                return data_comp.data
        try:
            return np.asarray(np.unique(np.concatenate([_get_component(layer) for layer in self.layers])),  # noqa
                              dtype=float)
        except ValueError:
            # NOTE: this will result in caching an empty list
            return np.array([])

    def _set_slice_indicator_value(self, value):
        # this is a separate method so that viewers can override and map value if necessary
        # NOTE: on first call, this will initialize the indicator itself
        self.slice_indicator.value = value


class WithSliceSelection:
    @property
    def slice_index(self):
        # index in state.slices corresponding to the slice axis
        return 2

    @property
    def slice_component_label(self):
        slice_plg = self.jdaviz_helper.plugins.get('Slice', None)
        if slice_plg is None:  # pragma: no cover
            raise ValueError("slice plugin must be activated to access slice_component_label")
        return slice_plg._obj.slice_indicator_viewers[0].slice_component_label

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @cached_property
    def slice_values(self):
        # TODO: add support for multiple cubes (but then slice selection needs to be more complex)
        # if slice_index is 0, then we want the equivalent of [:, 0, 0]
        # if slice_index is 1, then we want the equivalent of [0, :, 0]
        # if slice_index is 2, then we want the equivalent of [0, 0, :]
        take_inds = [2, 1, 0]
        take_inds.remove(self.slice_index)
        converted_axis = np.array([])
        for layer in self.layers:
            world_comp_ids = layer.layer.data.world_component_ids
            if self.slice_index >= len(world_comp_ids):
                # Case where 2D image is loaded in image viewer
                continue

            # Retrieve display units
            slice_display_units = self.jdaviz_app._get_display_unit(
                self.slice_display_unit_name
            )

            try:
                # Retrieve layer data and units using the slice index of the world components ids
                data_comp = layer.layer.data.get_component(world_comp_ids[self.slice_index])
            except (AttributeError, KeyError):
                continue

            data = np.asarray(data_comp.data.take(0, take_inds[0]).take(0, take_inds[1]),  # noqa
                              dtype=float)

            # Convert to display units if applicable
            data_units = getattr(data_comp, 'units', None)
            if slice_display_units and data_units and slice_display_units != data_units:
                converted_axis = (data * u.Unit(data_units)).to_value(
                    slice_display_units,
                    equivalencies=u.spectral()
                )
            else:
                converted_axis = data

        return converted_axis

    @property
    def slice(self):
        return self.state.slices[self.slice_index]

    @slice.setter
    def slice(self, slice):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        slices = [0, 0, 0]
        slices[self.slice_index] = slice
        self.state.slices = tuple(slices)

    @property
    def slice_value(self):
        return self.slice_values[self.slice]

    @slice_value.setter
    def slice_value(self, slice_value):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        # find the slice nearest slice_value
        slice_values = self.slice_values
        if not len(slice_values):
            return
        self.slice = np.argmin(abs(slice_values - slice_value))


@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(JdavizViewerMixin, WithSliceSelection, BqplotImageView):
    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:pixelboxzoommatch', 'jdaviz:boxzoom',
                     'jdaviz:pixelpanzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                     'bqplot:circannulus'],
                    ['jdaviz:spectrumperspaxel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide reference from state back to viewer to use for zoom syncing
        self.state._viewer = self

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        # Hide axes by default
        self.state.show_axes = False

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed
                           )

        self.hub.subscribe(self, AddDataMessage, handler=self._on_global_display_unit_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_global_display_unit_changed)

    @property
    def _default_spectrum_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_viewer_reference_name

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name

    @property
    def _default_uncert_viewer_reference_name(self):
        return self.jdaviz_helper._default_uncert_viewer_reference_name

    def _on_global_display_unit_changed(self, msg):
        # Clear cache of slice values when units change
        if 'slice_values' in self.__dict__:
            del self.__dict__['slice_values']

    def _initial_x_axis(self, *args):
        # Make sure that the x_att is correct on data load
        ref_data = self.state.reference_data
        if ref_data and ref_data.ndim == 3:
            for att_name in ["Right Ascension", "RA", "Galactic Longitude"]:
                if att_name in ref_data.component_ids():
                    x_att = att_name
                    self.state.x_att_world = ref_data.id[x_att]
                    break
            else:
                x_att = "Pixel Axis 0 [z]"
                self.state.x_att = ref_data.id[x_att]

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(SpecvizProfileView, WithSliceIndicator):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_tool_priority', ['jdaviz:selectslice'])
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._check_if_data_removed)

        # TODO: Find out why this is not working
        # self.hub.subscribe(self, DataCollectionDeleteMessage,
        #                    handler=self._check_if_data_removed)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._check_if_data_added)

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed)

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name

    def _on_global_display_unit_changed(self, msg=None):
        # Clear cache of slice values when units change
        if 'slice_values' in self.__dict__:
            del self.__dict__['slice_values']

    def _check_if_data_removed(self, msg):
        # isinstance and the data uuid check will be true for the data
        # that is being removed
        self.figure.marks = [m for m in self.figure.marks
                             if not (isinstance(m, ShadowSpatialSpectral)
                                     and m.data_uuid == msg.data.uuid)]
        self._on_global_display_unit_changed()

    def _check_if_data_added(self, msg=None):
        # When data is added, make sure that all spatial subset layers
        # that correspond with that data are checked for intersections
        # with spectral subset layers
        for layer in self.state.layers:
            if layer.layer.data.label == msg.data.label:
                if (isinstance(layer.layer, GroupedSubset) and
                        get_subset_type(layer.layer.subset_state) == 'spatial'):
                    self._expected_subset_layer_default(layer)
        self._on_global_display_unit_changed()

    def _is_spatial_subset(self, layer):
        subset_state = getattr(layer.layer, 'subset_state', None)
        return get_subset_type(subset_state) == 'spatial'

    def _get_spatial_subset_layers(self, data_label=None):
        if data_label:
            return [ls for ls in self.state.layers if (ls.layer.data.label == data_label and
                                                       self._is_spatial_subset(ls))]
        return [ls for ls in self.state.layers if self._is_spatial_subset(ls)]

    def _is_spectral_subset(self, layer):
        subset_state = getattr(layer.layer, 'subset_state', None)
        return get_subset_type(subset_state) == 'spectral'

    def _get_spectral_subset_layers(self, data_label=None):
        if data_label:
            return [ls for ls in self.state.layers if (ls.layer.data.label == data_label and
                                                       self._is_spectral_subset(ls))]
        return [ls for ls in self.state.layers if self._is_spectral_subset(ls)]

    def _get_marks_for_layers(self, layers):
        layers_list = list(self.state.layers)
        # here we'll assume that all custom marks are subclasses of Lines/GL but don't directly
        # use Lines/LinesGL (so an isinstance check won't be sufficient here)
        layer_marks = self.native_marks
        # and now we'll assume that the marks are in the same order as the layers, this should
        # be the case as long as the order isn't manually resorted.  If for any reason the layer
        # is added but the mark has not yet been created, this will ignore that entry rather than
        # raising an IndexError.
        inds = [layers_list.index(layer) for layer in layers]
        return [layer_marks[ind] for ind in inds if ind < len(layer_marks)]

    def _on_subset_delete(self, msg):
        # delete any ShadowSpatialSpectral mark for which either of the spectral or spatial marks
        # no longer exists by matching the uuid of the msg subset to the uuid of the subsets
        # in ShadowSpatialSpectral
        super()._on_subset_delete(msg)
        self.figure.marks = [m for m in self.figure.marks
                             if not (isinstance(m, ShadowSpatialSpectral)
                                     and msg.subset.uuid in [m.spatial_uuid, m.spectral_uuid])]

    def _expected_subset_layer_default(self, layer_state):
        """
        This gets called whenever the layer of an expected new subset is added, we want to set the
        default for the linewidth depending on whether it is spatial or spectral, and handle
        creating any necessary marks for spatial-spectral subset intersections.
        """
        def _marks_are_same(m, other):
            # Check if ShadowSpatialSpectral mark already exists for particular
            # data, spatial subset, and spectral subset combo
            if (m.data_uuid == other.data_uuid
                and m.spatial_uuid == other.spatial_uuid
                    and m.spectral_uuid == other.spectral_uuid):
                return True
            return False

        def _is_unique(m):
            unique = True
            for m in existing_shadows_for_data:
                if _marks_are_same(m, new_shadow):
                    unique = False
                    break
            return unique

        super()._expected_subset_layer_default(layer_state)
        subset_type = get_subset_type(layer_state.layer)
        if subset_type is None:
            return

        this_mark = self._get_marks_for_layers([layer_state])[0]
        # new ShadowSpatialSpectral marks to be added
        new_marks = []
        # ShadowSpatialSpectral marks that already exists in the viewer
        existing_shadows_for_data = [m for m in self.figure.marks
                                     if isinstance(m, ShadowSpatialSpectral)]
        if subset_type == 'spatial':
            layer_state.linewidth = 1

            # need to add marks for every intersection between THIS spatial subset and ALL spectral
            # subset marks corresponding to this data
            spectral_layers = [sub_layer for sub_layer in
                               self._get_spectral_subset_layers(layer_state.layer.data.label)]
            spectral_marks = self._get_marks_for_layers(spectral_layers)

            for index, spectral_mark in enumerate(spectral_marks):
                new_shadow = ShadowSpatialSpectral(spatial_spectrum_mark=this_mark,
                                                   spectral_subset_mark=spectral_mark,
                                                   spatial_uuid=layer_state.layer.uuid,
                                                   spectral_uuid=spectral_layers[index].layer.uuid,
                                                   data_uuid=layer_state.layer.data.uuid)
                if _is_unique(new_shadow):
                    new_marks.append(new_shadow)

            # change opacity for live-collapsed spectra from spatial subsets in Cubeviz:
            spatial_layers = [sub_layer for sub_layer in
                              self._get_spatial_subset_layers(layer_state.layer.data.label)]
            spatial_marks = self._get_marks_for_layers(spatial_layers)
            for layer, mark in zip(spatial_layers, spatial_marks):
                # update profile opacities for spatial subset:
                if isinstance(mark, Lines):
                    mark.set_trait(
                        'opacities',
                        # set the alpha for the spectrum in the profile viewer
                        # to be 50% more opaque than the alpha for the spatial subset
                        # in the flux-viewer
                        [min(1.5 * layer.alpha, 1)]
                    )

        elif subset_type == 'spectral':
            # need to add marks for every intersection between THIS spectral subset and ALL spatial
            # subset marks corresponding to this data
            spatial_layers = [sub_layer for sub_layer in
                              self._get_spatial_subset_layers(layer_state.layer.data.label)]
            spatial_marks = self._get_marks_for_layers(spatial_layers)
            for index, spatial_mark in enumerate(spatial_marks):
                new_shadow = ShadowSpatialSpectral(spatial_spectrum_mark=spatial_mark,
                                                   spectral_subset_mark=this_mark,
                                                   spatial_uuid=spatial_layers[index].layer.uuid,
                                                   spectral_uuid=layer_state.layer.uuid,
                                                   data_uuid=layer_state.layer.data.uuid)
                if _is_unique(new_shadow):
                    new_marks.append(new_shadow)

        else:
            return
        # NOTE: += or append won't pick up on change
        self.figure.marks = self.figure.marks + new_marks
