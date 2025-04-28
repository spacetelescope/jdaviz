import numpy as np
import astropy.units as u
from astropy.nddata import NDDataArray

from functools import cached_property
from traitlets import Bool, Float, List, Unicode, observe, Int
from glue.core.message import (
    DataCollectionAddMessage, SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
)

from jdaviz.core.events import SnackbarMessage, SliceValueUpdatedMessage
from jdaviz.core.marks import PluginLine
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        ApertureSubsetSelectMixin,
                                        ApertureSubsetSelect,
                                        AddResultsMixin,
                                        skip_if_not_tray_instance,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner, with_temp_disable)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.configs.cubeviz.plugins.viewers import WithSliceIndicator


__all__ = ['RampExtraction']

rng = np.random.default_rng(seed=42)


@tray_registry(
    'ramp-extraction', label="Ramp Extraction", viewer_requirements='profile'
)
class RampExtraction(PluginTemplateMixin, ApertureSubsetSelectMixin,
                     DatasetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Ramp Extraction Plugin Documentation <ramp-extraction>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``aperture`` (:class:`~jdaviz.core.template_mixin.ApertureSubsetSelect`):
      Subset to use for the ramp extraction, or ``Entire Cube``.
    * ``aperture_method`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Method to use for extracting a ramp profile
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`extract`
    """
    template_file = __file__, "ramp_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)
    show_live_preview = Bool(False).tag(sync=True)
    show_subset_preview = Bool(True).tag(sync=True)
    subset_preview_warning = Bool(False).tag(sync=True)
    subset_preview_limit = Int(250).tag(sync=True)

    active_step = Unicode().tag(sync=True)

    resulting_product_name = Unicode("ramp").tag(sync=True)
    do_auto_extraction = True

    slice_group_value = Float().tag(sync=True)

    function_items = List().tag(sync=True)
    function_selected = Unicode('Mean').tag(sync=True)
    filename = Unicode().tag(sync=True)
    extraction_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)

    aperture_method_items = List().tag(sync=True)
    aperture_method_selected = Unicode('Center').tag(sync=True)

    conflicting_aperture_and_function = Bool(False).tag(sync=True)
    conflicting_aperture_error_message = Unicode('Aperture method Exact cannot be selected along'
                                                 ' with Min or Max.').tag(sync=True)

    # export_enabled controls whether saving to a file is enabled via the UI.  This
    # is a temporary measure to allow server-installations to disable saving server-side until
    # saving client-side is supported
    export_enabled = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Extract a ramp from a ramp cube.'

        self.dataset.filters = ['is_flux_cube']

        # TODO: in the future this could be generalized with support in SelectPluginComponent
        self.aperture._default_text = 'Entire Cube'
        self.aperture._manual_options = ['Entire Cube']
        self.aperture.items = [{"label": "Entire Cube"}]
        self.aperture._subset_selected_changed_callback = self._update_extract
        # need to reinitialize choices since we overwrote items and some subsets may already
        # exist.
        self.aperture._initialize_choices()
        self.aperture.select_default()

        self.extracted_ramp = None

        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Median', 'Min', 'Max', 'Sum']
        )
        self._set_default_results_label()
        self.add_results.viewer.filters = ['is_slice_indicator_viewer']

        self.session.hub.subscribe(self, SliceValueUpdatedMessage,
                                   handler=self._on_slice_changed)

        self.session.hub.subscribe(self, DataCollectionAddMessage,
                                   handler=self._on_data_added)

        self.session.hub.subscribe(self, SubsetCreateMessage,
                                   handler=self._on_subset_update)

        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._on_subset_update)

        self.session.hub.subscribe(self, SubsetDeleteMessage,
                                   handler=self._on_subset_delete)

        self._update_disabled_msg()

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

    @property
    def integration_viewer(self):
        viewer = self.app.get_viewer(
            self.app._jdaviz_helper._default_integration_viewer_reference_name
        )
        return viewer

    def _on_data_added(self, msg={}):
        # only perform the default collapse after the first data load:
        if len(self.app._jdaviz_helper.cube_cache) and not self.extraction_available:
            self.extract(add_data=True)
            self.integration_viewer._initialize_x_axis()

    def _on_subset_update(self, msg={}):
        if not hasattr(self.app._jdaviz_helper, 'cube_cache'):
            # if called before fully initialized
            return

        subset_lbl = msg.subset.label
        color = msg.subset.style.color
        subset = self.app.get_subsets(subset_lbl)[0]
        region = subset['region']

        if region is None:
            return

        # glue region has transposed coords relative to cached cube:
        region_mask = region.to_mask().to_image(
            self.cube.shape[:-1][::-1]
        ).astype(bool).T
        cube_subset = self.cube[region_mask]  # shape: (N pixels extracted, M groups)

        n_pixels_in_extraction = cube_subset.shape[0]

        if n_pixels_in_extraction < self.subset_preview_limit:
            self.subset_preview_warning = False
            select_from_cube_subset = Ellipsis
        else:
            self.subset_preview_warning = True
            select_from_cube_subset = rng.integers(
                0, n_pixels_in_extraction, size=self.subset_preview_limit
            )

        marks = [
            PluginLine(
                self.integration_viewer, x=np.arange(cube_subset.shape[1]), y=y,
                stroke_width=1, colors=[color], opacities=[0.25], label=subset_lbl,
                visible=self._subset_preview_visible and subset_lbl == self.aperture.selected
            )
            for y in cube_subset[select_from_cube_subset]
        ]

        self.integration_viewer.figure.marks = [
            mark for mark in self.integration_viewer.figure.marks
            if getattr(mark, 'label', None) != subset_lbl
        ] + marks

        self.integration_viewer.reset_limits()

    def _on_subset_delete(self, msg={}):
        subset_lbl = msg.subset.label
        self.integration_viewer.figure.marks = [
            mark for mark in self.integration_viewer.figure.marks
            if getattr(mark, 'label', None) != subset_lbl
        ]

    @observe('is_active', 'show_subset_preview', 'aperture_selected')
    def _update_subset_previews(self, msg={}):
        # remove preview marks for non-selected subsets

        if not hasattr(self.app._jdaviz_helper, '_default_integration_viewer_reference_name'):
            return

        for mark in self.integration_viewer.figure.marks:
            if isinstance(mark, PluginLine) and mark.label is not None:
                new_visibility = (
                    self._subset_preview_visible and
                    self.aperture.selected == mark.label
                )
                if mark.visible != new_visibility:
                    mark.visible = new_visibility

        self.integration_viewer.reset_limits()

    @property
    def _subset_preview_visible(self):
        return self.show_subset_preview and self.is_active

    @property
    def user_api(self):
        expose = [
            'dataset', 'function', 'aperture', 'add_results', 'extract'
        ]

        return PluginUserApi(self, expose=expose)

    @observe('dataset_items')
    def _update_disabled_msg(self, msg={}):
        for data in self.app.data_collection:
            if data.data.ndim == 3:
                self.disabled_msg = ''
                break
        else:
            # no cube-like data loaded.  Once loaded, the parser will unset this
            self.disabled_msg = (
                f"{self.__class__.__name__} requires a 3d cube dataset to be loaded, "
                "please load data to enable this plugin."
            )

    @property
    def live_update_subscriptions(self):
        return {'data': ('dataset',), 'subset': ('aperture', )}

    def __call__(self, add_data=True):
        return self.extract(add_data=add_data)

    @property
    def slice_display_unit_name(self):
        return 'temporal'

    @property
    def spatial_axes(self):
        # Collapse an e.g. 3D ramp cube to 1D ramp profile, assuming that last axis
        # is always the group/resultant index
        return (0, 1)

    @property
    def slice_indicator_viewers(self):
        return [v for v in self.app._viewer_store.values() if isinstance(v, WithSliceIndicator)]

    @observe('active_step', 'is_active')
    def _active_step_changed(self, *args):
        self.aperture._set_mark_visiblities(self.active_step in ('', 'ap', 'extract'))

    @property
    def slice_plugin(self):
        return self.app._jdaviz_helper.plugins['Slice']

    def _extract_in_new_instance(self, dataset=None, function='Mean', subset_lbl=None,
                                 auto_update=False, add_data=False):
        # create a new instance of the Ramp Extraction plugin (to not affect the instance in
        # the tray) and extract the entire cube with defaults.
        plg = self.new()
        plg.dataset.selected = self.dataset.selected
        if subset_lbl is not None:
            plg.aperture.selected = subset_lbl
        plg.function.selected = function
        plg.add_results.auto_update_result = auto_update
        # all other settings remain at their plugin defaults
        return plg(add_data=add_data)

    def _on_slice_changed(self, msg):
        self.slice_group_value = msg.value

    @observe('function_selected', 'aperture_method_selected')
    def _update_aperture_method_on_function_change(self, *args):
        if (self.function_selected.lower() in ('min', 'max') and
                self.aperture_method_selected.lower() != 'center'):
            self.conflicting_aperture_and_function = True
        else:
            self.conflicting_aperture_and_function = False

    @property
    def cube(self):
        return self.app._jdaviz_helper.cube_cache.get(self.dataset.selected)

    @property
    def slice_display_unit(self):
        x_display_unit = self.app._get_display_unit(self.slice_display_unit_name)
        if x_display_unit not in ['None', None]:
            return u.Unit(x_display_unit)
        return u.dimensionless_unscaled

    @property
    def aperture_weight_mask(self):
        cube_shape = self.cube.shape
        if self.aperture.selected != self.aperture.default_text:

            # note: glue subset mask is transposed relative to cube
            region_mask = self.app.get_subsets(
                subset_name=self.aperture.selected
            )[0]['region'].to_mask().to_image(
                cube_shape[:-1]
            ).astype(bool).T
            return region_mask

        return np.ones(cube_shape[:-1]).astype(bool)

    def _extract_from_aperture(self, **kwargs):
        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the ramp
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        selected_func = self.function_selected.lower()

        if not isinstance(self.aperture, ApertureSubsetSelect):
            raise ValueError("aperture must be an ApertureSubsetSelect object")

        nddata = self.cube
        mask = self.aperture_weight_mask

        if nddata.mask is not None:
            mask = mask & ~nddata.mask

        collapsed = getattr(np, selected_func)(
            nddata.data[mask],
            # after the fancy indexing above, axis=1 corresponds to groups, and
            # operations over axis=0 corresponds to individual pixels:
            axis=0
        )
        if nddata.unit is not None:
            collapsed <<= nddata.unit

        def expand(x):
            # put the resulting 1D profile (counts vs. groups) into the
            # third dimension, which is the group dimension in the
            # original 3D cube:
            return np.expand_dims(x, axis=(0, 1))

        return NDDataArray(
            data=expand(collapsed),
            meta=nddata.meta
        )

    def _preview_x_from_extracted(self, extracted):
        return np.arange(extracted.shape[-1])

    def _preview_y_from_extracted(self, extracted):
        return extracted.data

    @with_spinner()
    def extract(self, add_data=True, **kwargs):
        """
        Extract the ramp profile from the data cube according to the plugin inputs.

        Parameters
        ----------
        add_data : bool, optional
            Whether to load the resulting data back into the application according to
            ``add_results``.
        kwargs : dict
            Additional keyword arguments passed to the NDDataArray collapse operation.
            Examples include ``propagate_uncertainties`` and ``operation_ignores_mask``.
        """
        if self.conflicting_aperture_and_function:
            raise ValueError(self.conflicting_aperture_error_message)

        selected_func = self.function_selected.lower()
        ndd = self._extract_from_aperture(**kwargs)
        self.extracted_ramp = ndd
        self.extraction_available = True
        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"extracted_{selected_func}_{fname_label}.fits"

        if add_data:
            if default_color := self.aperture.selected_item.get('color', None):
                ndd.meta['_default_color'] = default_color
            self.add_results.add_results_from_plugin(ndd)

            snackbar_message = SnackbarMessage(
                f"{self.resulting_product_name.title()} extracted successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        return ndd

    def vue_ramp_extraction(self, *args, **kwargs):
        try:
            self.extract(add_data=True)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Extraction failed: {repr(e)}",
                sender=self, color="error"))

    @observe('aperture_selected', 'function_selected')
    def _set_default_results_label(self, event={}):
        if not hasattr(self, 'aperture'):
            return
        if self.aperture.selected == self.aperture.default_text:
            self.results_label_default = (f"{self.resulting_product_name.title()} "
                                          f"({self.function_selected.lower()})")

        else:
            self.results_label_default = (f"{self.resulting_product_name.title()} "
                                          f"({self.aperture_selected}, "
                                          f"{self.function_selected.lower()})")

    @cached_property
    def marks(self):
        if not self._tray_instance:
            return {}
        # TODO: iterate over self.slice_indicator_viewers and handle adding/removing viewers

        sv = self.slice_indicator_viewers[0]
        marks = {'extract': PluginLine(sv, visible=self.is_active)}
        sv.figure.marks = sv.figure.marks + [marks['extract'],]
        return marks

    def _clear_marks(self):
        for mark in self.marks.values():
            if getattr(mark, 'visible', False):
                mark.visible = False

    @observe('is_active', 'show_live_preview',
             'dataset_selected', 'aperture_selected',
             'function_selected',
             'aperture_method_selected',
             'previews_temp_disabled')
    def _live_update_marks(self, event={}):
        self._update_marks(event)

    @skip_if_not_tray_instance()
    def _update_marks(self, event={}):
        visible = self.show_live_preview and self.is_active

        if not visible:
            self._clear_marks()
            return

        # ensure the correct visibility, always (whether or not there have been updates)
        if hasattr(self.marks['extract'], 'visible'):
            self.marks['extract'].visible = True

        # _live_update will skip if no updates since last active
        self._live_update_extract(event)

    @skip_if_no_updates_since_last_active()
    @with_temp_disable(timeout=0.4)
    def _live_update_extract(self, event={}):
        self._update_extract()

    @skip_if_not_tray_instance()
    def _update_extract(self):
        try:
            ext = self.extract(add_data=False)
        except (ValueError, Exception):
            self._clear_marks()
            return False

        self.marks['extract'].update_xy(self._preview_x_from_extracted(ext),
                                        self._preview_y_from_extracted(ext))
