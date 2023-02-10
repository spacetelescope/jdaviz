from glue.core import BaseData
from glue.core.subset import RoiSubsetState, RangeSubsetState
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicatorMarks, ShadowSpatialSpectral
from jdaviz.configs.cubeviz.helper import layer_is_cube_image_data
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView

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
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        # NOTE: super will initialize nested toolbar with
        # default_tool_priority=['jdaviz:selectslice']
        super().__init__(*args, **kwargs)

        self._default_flux_viewer_reference_name = kwargs.get(
            "flux_viewer_reference_name", "flux-viewer"
        )

    def _is_spatial_subset(self, layer):
        # spatial subset layers will have the same data-label as the collapsed flux cube
        ref_data_label = self.state.reference_data.label
        return (isinstance(getattr(layer.layer, 'subset_state', None), RoiSubsetState)
                and layer.layer.data.label == ref_data_label)

    def _get_spatial_subset_layers(self):
        return [ls for ls in self.state.layers if self._is_spatial_subset(ls)]

    def _is_spectral_subset(self, layer):
        ref_data_label = self.layers[0].layer.data.label
        return (isinstance(getattr(layer.layer, 'subset_state', None), RangeSubsetState)
                and layer.layer.data.label == ref_data_label)

    def _get_spectral_subset_layers(self):
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
        # no longer exists
        spectral_marks = self._get_marks_for_layers(self._get_spectral_subset_layers())
        spatial_marks = self._get_marks_for_layers(self._get_spatial_subset_layers())
        self.figure.marks = [m for m in self.figure.marks
                             if not (isinstance(m, ShadowSpatialSpectral) and
                                     (m.spatial_spectrum_mark in spatial_marks or
                                      m.spectral_subset_mark in spectral_marks))]

    def _expected_subset_layer_default(self, layer_state):
        """
        This gets called whenever the layer of an expected new subset is added, we want to set the
        default for the linewidth depending on whether it is spatial or spectral, and handle
        creating any necessary marks for spatial-spectral subset intersections.
        """
        super()._expected_subset_layer_default(layer_state)

        if not (self._is_spatial_subset(layer_state) or self._is_spectral_subset(layer_state)):
            return

        this_mark = self._get_marks_for_layers([layer_state])[0]

        new_marks = []

        if isinstance(layer_state.layer.subset_state, RoiSubsetState):
            layer_state.linewidth = 1

            # need to add marks for every intersection between THIS spatial subset and ALL spectral
            spectral_marks = self._get_marks_for_layers(self._get_spectral_subset_layers())
            for spectral_mark in spectral_marks:
                new_marks += [ShadowSpatialSpectral(this_mark, spectral_mark)]

        else:
            layer_state.linewidth = 3

            # need to add marks for every intersection between THIS spectral subset and ALL spatial
            spatial_marks = self._get_marks_for_layers(self._get_spatial_subset_layers())
            for spatial_mark in spatial_marks:
                new_marks += [ShadowSpatialSpectral(spatial_mark, this_mark)]

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
