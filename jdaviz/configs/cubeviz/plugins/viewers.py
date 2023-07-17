from glue.core import BaseData

from glue.core.subset_group import GroupedSubset
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicatorMarks, ShadowSpatialSpectral
from jdaviz.configs.cubeviz.helper import layer_is_cube_image_data
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.utils import get_subset_type
from jdaviz.core.events import AddDataMessage, RemoveDataMessage

__all__ = ['CubevizImageView', 'CubevizProfileView']


@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(JdavizViewerMixin, BqplotImageView):
    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoommatch', 'jdaviz:boxzoom',
                     'jdaviz:simplepanzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:circle', 'bqplot:rectangle', 'bqplot:ellipse'],
                    ['jdaviz:spectrumperspaxel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._default_flux_viewer_reference_name = kwargs.get(
            "flux_viewer_reference_name", "flux-viewer"
        )
        self._default_uncert_viewer_reference_name = kwargs.get(
            "uncert_viewer_reference_name", "uncert-viewer"
        )
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

    @property
    def active_image_layer(self):
        """Active image layer in the viewer, if available."""
        # Find visible layers
        visible_layers = [layer for layer in self.state.layers
                          if (layer.visible and layer_is_cube_image_data(layer.layer))]

        if len(visible_layers) == 0:
            return None

        return visible_layers[-1]

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
class CubevizProfileView(SpecvizProfileView):
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

        self._default_flux_viewer_reference_name = kwargs.get(
            "flux_viewer_reference_name", "flux-viewer"
        )
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._check_if_data_removed)

        # TODO: Find out why this is not working
        # self.hub.subscribe(self, DataCollectionDeleteMessage,
        #                    handler=self._check_if_data_removed)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._check_if_data_added)

    def _check_if_data_removed(self, msg):
        # isinstance and the data uuid check will be true for the data
        # that is being removed
        self.figure.marks = [m for m in self.figure.marks
                             if not (isinstance(m, ShadowSpatialSpectral)
                                     and m.data_uuid == msg.data.uuid)]

    def _check_if_data_added(self, msg=None):
        # When data is added, make sure that all spatial subset layers
        # that correspond with that data are checked for intersections
        # with spectral subset layers
        for layer in self.state.layers:
            if layer.layer.data.label == msg.data.label:
                if (isinstance(layer.layer, GroupedSubset) and
                        get_subset_type(layer.layer.subset_state) == 'spatial'):
                    self._expected_subset_layer_default(layer)

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

    @property
    def slice_indicator(self):
        for mark in self.figure.marks:
            if isinstance(mark, SliceIndicatorMarks):
                return mark

        # SliceIndicatorMarks does not yet exist
        slice_indicator = SliceIndicatorMarks(self)
        self.figure.marks = self.figure.marks + slice_indicator.marks
        return slice_indicator

    def _update_slice_indicator(self, slice):
        self.slice_indicator.slice = slice
