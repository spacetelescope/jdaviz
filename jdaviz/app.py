import operator
import os
import pathlib
import re
import uuid
import warnings
import ipyvue
from astropy import units as u
from astropy.nddata import NDData, NDDataArray
from astropy.io import fits
from astropy.time import Time
from echo import (CallbackProperty, DictCallbackProperty,
                  ListCallbackProperty, delay_callback)
from ipygoldenlayout import GoldenLayout
from ipysplitpanes import SplitPanes
import numpy as np
from glue.config import data_translator, settings as glue_settings
from glue.core import HubListener
from glue.core.link_helpers import LinkSame, LinkSameWithUnits
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage,
                               SubsetUpdateMessage,
                               SubsetDeleteMessage)
from glue.core.roi import CircularROI, CircularAnnulusROI, EllipticalROI, RectangularROI
from glue.core.state_objects import State
from glue.core.subset import (RangeSubsetState, RoiSubsetState,
                              CompositeSubsetState, InvertState)
from glue.core.units import unit_converter
from glue_astronomy.spectral_coordinates import SpectralCoordinates
from glue_astronomy.translators.regions import roi_subset_state_to_region
from glue_jupyter.app import JupyterApplication
from glue_jupyter.common.toolbar_vuetify import read_icon
from glue_jupyter.state_traitlets_helpers import GlueState
from ipypopout import PopoutButton
from ipyvuetify import VuetifyTemplate
from ipywidgets import widget_serialization
from traitlets import Dict, Bool, List, Unicode, Any
from specutils import Spectrum, SpectralRegion
from specutils.utils.wcs_utils import SpectralGWCS

from jdaviz import __version__
from jdaviz import style_registry
from jdaviz.core.config import read_configuration, get_configuration
from jdaviz.core.events import (LoadDataMessage, NewViewerMessage, AddDataMessage,
                                SnackbarMessage, RemoveDataMessage, SubsetRenameMessage,
                                AddDataToViewerMessage, RemoveDataFromViewerMessage,
                                ViewerAddedMessage, ViewerRemovedMessage,
                                ViewerRenamedMessage, ChangeRefDataMessage,
                                IconsUpdatedMessage)
from jdaviz.core.registries import (tool_registry, tray_registry,
                                    viewer_registry, viewer_creator_registry,
                                    data_parser_registry, loader_resolver_registry)
from jdaviz.core.tools import ICON_DIR
from jdaviz.utils import (SnackbarQueue, alpha_index, data_has_valid_wcs,
                          layer_is_table_data, MultiMaskSubsetState,
                          _wcs_only_label)
from jdaviz.core.custom_units_and_equivs import SPEC_PHOTON_FLUX_DENSITY_UNITS, enable_spaxel_unit
from jdaviz.core.unit_conversion_utils import (check_if_unit_is_per_solid_angle,
                                               combine_flux_and_angle_units,
                                               flux_conversion_general,
                                               spectral_axis_conversion,
                                               supported_sq_angle_units,
                                               viewer_flux_conversion_equivalencies)

__all__ = ['Application', 'ALL_JDAVIZ_CONFIGS', 'UnitConverterWithSpectral']

SplitPanes()
GoldenLayout()

enable_spaxel_unit()

# This shows up repeatedly when doing many operations, I think it's reasonable to disable it
warnings.filterwarnings('ignore', message="The unit 'Angstrom' has been deprecated"
                        "in the VOUnit standard")

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')
EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])
ALL_JDAVIZ_CONFIGS = ['cubeviz', 'specviz', 'specviz2d', 'mosviz', 'imviz']


@unit_converter('custom-jdaviz')
class UnitConverterWithSpectral:
    def equivalent_units(self, data, cid, units):
        if (getattr(data, '_importer', None) == 'ImageImporter' and
                u.Unit(data.get_component(cid).units).physical_type == 'surface brightness'):
            all_flux_units = SPEC_PHOTON_FLUX_DENSITY_UNITS + ['ct']
            angle_units = supported_sq_angle_units()
            all_sb_units = combine_flux_and_angle_units(all_flux_units, angle_units)

            list_of_units = set(list(map(str, u.Unit(units).find_equivalent_units(
                include_prefix_units=True))) + all_flux_units + all_sb_units
                )
        elif cid.label in ("flux"):
            eqv = u.spectral_density(1 * u.m)  # Value does not matter here.
            all_flux_units = SPEC_PHOTON_FLUX_DENSITY_UNITS + ['ct']
            angle_units = supported_sq_angle_units()
            all_sb_units = combine_flux_and_angle_units(all_flux_units, angle_units)

            # list of all possible units for spectral y axis, independent of data loaded
            #
            list_of_units = set(list(map(str, u.Unit(units).find_equivalent_units(
                include_prefix_units=True, equivalencies=eqv))) + all_flux_units + all_sb_units
                )
        else:  # spectral axis
            # prefer Hz over Bq and um over micron
            exclude = {'Bq', 'micron'}
            list_of_units = set(list(map(str, u.Unit(units).find_equivalent_units(
                include_prefix_units=True, equivalencies=u.spectral())))) - exclude
        return list_of_units

    def to_unit(self, data, cid, values, original_units, target_units):
        # Given a glue data object (data), a component ID (cid), the values
        # to convert, and the original and target units of the values, this method
        # should return the converted values. Note that original_units
        # gives the units of the values array, which might not be the same
        # as the original native units of the component in the data.

        if cid.label == 'Pixel Axis 0 [z]' and target_units == '':
            # handle ramps loaded into Rampviz by avoiding conversion
            # of the groups axis:
            return values
        elif (getattr(data, '_importer', None) == 'ImageImporter' and
              u.Unit(data.get_component(cid).units).physical_type == 'surface brightness'):
            # handle surface brightness units in image-like data
            return (values * u.Unit(original_units)).to_value(target_units)
        elif cid.label in ("flux"):
            try:
                spec = data.get_object(cls=Spectrum)
            except RuntimeError:
                data = data.get_object(cls=NDDataArray)
                spec = Spectrum(flux=data.data * u.Unit(original_units))
            # equivalencies for flux/surface brightness conversions
            viewer_equivs = viewer_flux_conversion_equivalencies(values, spec)
            return flux_conversion_general(values, original_units,
                                           target_units, viewer_equivs,
                                           with_unit=False)
        else:  # spectral axis
            return spectral_axis_conversion(values, original_units, target_units)


# Set default opacity for data layers to 1 instead of 0.8 in
# some glue-core versions
glue_settings.DATA_ALPHA = 1

# Enable spectrum unit conversion.
glue_settings.UNIT_CONVERTER = 'custom-jdaviz'

custom_components = {'j-tooltip': 'components/tooltip.vue',
                     'j-external-link': 'components/external_link.vue',
                     'j-docs-link': 'components/docs_link.vue',
                     'j-layer-viewer-icon': 'components/layer_viewer_icon.vue',
                     'j-layer-viewer-icon-stylized': 'components/layer_viewer_icon_stylized.vue',
                     'j-loader-panel': 'components/loader_panel.vue',
                     'j-new-viewer-panel': 'components/new_viewer_panel.vue',
                     'j-loader': 'components/loader.vue',
                     'j-viewer-creator': 'components/viewer_creator.vue',
                     'j-tray-plugin': 'components/tray_plugin.vue',
                     'j-play-pause-widget': 'components/play_pause_widget.vue',
                     'j-plugin-section-header': 'components/plugin_section_header.vue',
                     'j-number-uncertainty': 'components/number_uncertainty.vue',
                     'j-plugin-popout': 'components/plugin_popout.vue',
                     'j-multiselect-toggle': 'components/multiselect_toggle.vue',
                     'j-subset-icon': 'components/subset_icon.vue',
                     'j-plugin-live-results-icon': 'components/plugin_live_results_icon.vue',
                     'j-child-layer-icon': 'components/child_layer_icon.vue',
                     'j-about-menu': 'components/about_menu.vue',
                     'plugin-previews-temp-disabled': 'components/plugin_previews_temp_disabled.vue',  # noqa
                     'plugin-table': 'components/plugin_table.vue',
                     'plugin-select': 'components/plugin_select.vue',
                     'plugin-select-filter': 'components/plugin_select_filter.vue',
                     'plugin-dataset-select': 'components/plugin_dataset_select.vue',
                     'plugin-subset-select': 'components/plugin_subset_select.vue',
                     'plugin-viewer-select': 'components/plugin_viewer_select.vue',
                     'plugin-layer-select': 'components/plugin_layer_select.vue',
                     'plugin-layer-select-tabs': 'components/plugin_layer_select_tabs.vue',
                     'plugin-editable-select': 'components/plugin_editable_select.vue',
                     'plugin-inline-select': 'components/plugin_inline_select.vue',
                     'plugin-inline-select-item': 'components/plugin_inline_select_item.vue',
                     'plugin-switch': 'components/plugin_switch.vue',
                     'plugin-action-button': 'components/plugin_action_button.vue',
                     'plugin-add-results': 'components/plugin_add_results.vue',
                     'plugin-auto-label': 'components/plugin_auto_label.vue',
                     'plugin-file-import-select': 'components/plugin_file_import_select.vue',
                     'plugin-slider': 'components/plugin_slider.vue',
                     'plugin-color-picker': 'components/plugin_color_picker.vue',
                     'plugin-input-header': 'components/plugin_input_header.vue',
                     'plugin-loaders-panel': 'components/plugin_loaders_panel.vue',
                     'glue-state-sync-wrapper': 'components/glue_state_sync_wrapper.vue',
                     'glue-state-select': 'components/glue_state_select.vue',
                     'data-menu-add': 'components/data_menu_add.vue',
                     'data-menu-remove': 'components/data_menu_remove.vue',
                     'data-menu-subset-edit': 'components/data_menu_subset_edit.vue',
                     'hover-api-hint': 'components/hover_api_hint.vue'}

_verbosity_levels = ('debug', 'info', 'warning', 'error')

# Register pure vue component. This allows us to do recursive component instantiation only in the
# vue component file
for name, path in custom_components.items():
    ipyvue.register_component_from_file(None, name,
                                        os.path.join(os.path.dirname(__file__), path))

ipyvue.register_component_from_file('g-viewer-tab', "container.vue", __file__)


style_registry.add((__file__, 'main_styles.vue'))


class ApplicationState(State):
    """
    The application state object contains all the current front-end state,
    including the loaded data name references, the active viewers, plugins,
    and layout.

    This state object allows for nested callbacks in mutable objects like
    dictionaries and makes it so incremental changes to nested values
    propagate to the traitlet in order to trigger a UI re-render.
    """
    drawer_content = CallbackProperty(
        '', docstring="Content shown in the tray drawer.")
    add_subtab = CallbackProperty(
        0, docstring="Index of the active subtab in the add sidebar.")
    settings_subtab = CallbackProperty(
        0, docstring="Index of the active subtab in the settings sidebar.")
    info_subtab = CallbackProperty(
        0, docstring="Index of the active subtab in the info sidebar.")
    jdaviz_version = CallbackProperty(
        __version__, docstring="Version of Jdaviz.")
    global_search = CallbackProperty(
        '', docstring="Global search string.")
    global_search_menu = CallbackProperty(
        False, docstring="Whether to show the global search menu.")
    show_toolbar_buttons = CallbackProperty(
        True, docstring="Whether to show app-level toolbar buttons (left of sidebar menu button).")
    show_api_hints = CallbackProperty(
        False, docstring="Whether to show API hints.")
    subset_mode_create = CallbackProperty(
        False, docstring="Whether to create a new subset.")

    snackbar = DictCallbackProperty({
        'show': False,
        'test': "",
        'color': None,
        'timeout': 3000,
        'loading': False
    }, docstring="State of the quick toast messages.")

    snackbar_queue = SnackbarQueue()

    settings = DictCallbackProperty({
        'data': {
            'auto_populate': False,
            'parser': None
        },
        'visible': {
            'menu_bar': True,
            'toolbar': True,
            'tray': True,
            'tab_headers': True,
        },
        'dense_toolbar': True,
        'server_is_remote': False,  # sets some defaults, should be set before loading the config
        'context': {
            'notebook': {
                'max_height': '600px'
            }
        },
        'layout': {
        }
    }, docstring="Top-level application settings.")

    icons = DictCallbackProperty({
        'radialtocheck': read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml'),
        'checktoradial': read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml'),
        'nuer': read_icon(os.path.join(ICON_DIR, 'right-east.svg'), 'svg+xml'),
        'nuel': read_icon(os.path.join(ICON_DIR, 'left-east.svg'), 'svg+xml'),
        'api': read_icon(os.path.join(ICON_DIR, 'api.svg'), 'svg+xml'),
        'api-lock': read_icon(os.path.join(ICON_DIR, 'api_lock.svg'), 'svg+xml'),
    }, docstring="Custom application icons")

    viewer_icons = DictCallbackProperty({}, docstring="Indexed icons (numbers) for viewers across the app")  # noqa
    layer_icons = DictCallbackProperty({}, docstring="Indexed icons (letters) for layers across the app")  # noqa

    dev_loaders = CallbackProperty(
        False, docstring='Whether to enable developer mode for new loaders infrastructure')
    loader_items = ListCallbackProperty(
        docstring="List of loaders available to the application.")
    loader_selected = CallbackProperty(
        '', docstring="Active loader shown in the loaders panel.")
    new_viewer_items = ListCallbackProperty(
        docstring="List of new viewer items available to the application.")
    new_viewer_selected = CallbackProperty(
        '', docstring="Active new viewer shown in the new viewers panel.")

    data_items = ListCallbackProperty(
        docstring="List of data items parsed from the Glue data collection.")

    tool_items = ListCallbackProperty(
        docstring="Collection of toolbar items displayed in the application.")

    tray_items = ListCallbackProperty(
        docstring="List of plugins displayed in the sidebar tray area.")

    tray_items_open = CallbackProperty(
        [], docstring="The plugin(s) opened in sidebar tray area.")

    tray_items_filter = CallbackProperty(
        '', docstring='User-filter on tray items')

    stack_items = ListCallbackProperty(
        docstring="Nested collection of viewers constructed to support the "
                  "Golden Layout viewer area.")
    viewer_items = ListCallbackProperty(
        docstring="List (flat) of viewer objects")

    style_widget = CallbackProperty(
        '', docstring="Jupyter widget that won't be displayed but can apply css to the app"
    )


class Application(VuetifyTemplate, HubListener):
    """
    The main application object containing implementing the ipyvue/vuetify
    template instructions for composing the interface.
    """
    _metadata = Dict({"mount_id": "content"}).tag(sync=True)

    state = GlueState().tag(sync=True)

    template_file = __file__, "app.vue"

    loading = Bool(False).tag(sync=True)
    config = Unicode("").tag(sync=True)
    api_hints_obj = Unicode("").tag(sync=True)  # will use config if not defined
    vdocs = Unicode("").tag(sync=True)
    docs_link = Unicode("").tag(sync=True)
    popout_button = Any().tag(sync=True, **widget_serialization)
    style_registry_instance = Any().tag(sync=True, **widget_serialization)
    invisible_children = List(Any()).tag(sync=True, **widget_serialization)
    golden_layout_state = Dict(default_value=None, allow_none=True).tag(sync=True)
    force_open_about = Bool(False).tag(sync=True)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jdaviz_helper = None
        self._verbosity = 'warning'
        self._history_verbosity = 'info'
        self.popout_button = PopoutButton(self)
        self.style_registry_instance = style_registry.get_style_registry()

        # Generate a state object for this application to maintain the state of
        #  the user interface.
        self.state = ApplicationState()

        # The application handler stores the state of the data and the
        #  underlying glue infrastructure
        self._application_handler = JupyterApplication(
            settings={'new_subset_on_selection_tool_change': True,
                      'single_global_active_tool': False})

        # Add a reference to this application to the Glue session object. This
        # allows the jdaviz Application object to then be accessed via e.g.
        # viewer.session.jdaviz_app
        self._application_handler.session.jdaviz_app = self

        # Create a dictionary for holding non-ipywidget viewer objects so we
        #  can reference their state easily since glue does not store viewers
        self._viewer_store = {}

        from jdaviz.core.events import PluginTableAddedMessage, PluginPlotAddedMessage
        self._plugin_tables = {}
        self.hub.subscribe(self, PluginTableAddedMessage,
                           handler=self._on_plugin_table_added)
        self._plugin_plots = {}
        self.hub.subscribe(self, PluginPlotAddedMessage,
                           handler=self._on_plugin_plot_added)

        # Convenient reference of all existing subset names
        self._reserved_labels = set([])

        # Parse the yaml configuration file used to compose the front-end UI
        self.load_configuration(configuration)

        # If true, link data on load. If false, do not link data to speed up
        # data loading
        self.auto_link = kwargs.pop('auto_link', True)

        # Imviz linking
        self._align_by = 'pixels'
        if self.config == "imviz":
            self._wcs_fast_approximation = None

        # Subscribe to messages indicating that a new viewer needs to be
        #  created. When received, information is passed to the application
        #  handler to generate the appropriate viewer instance.
        self.hub.subscribe(self, NewViewerMessage,
                           handler=self._on_new_viewer)

        # Subscribe to messages indicating new data should be loaded into the
        #  application
        self.hub.subscribe(self, LoadDataMessage,
                           handler=lambda msg: self.load_data(msg.path))

        # Subscribe to the event fired when data is added to the application-
        #  level data collection object
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

        # Subscribe to the event fired when data is deleted from the
        #  application-level data collection object
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_deleted)

        self.hub.subscribe(self, AddDataToViewerMessage,
                           handler=lambda msg: self.add_data_to_viewer(
                               msg.viewer_reference, msg.data_label))

        self.hub.subscribe(self, RemoveDataFromViewerMessage,
                           handler=lambda msg: self.remove_data_from_viewer(
                               msg.viewer_reference, msg.data_label))

        # Subscribe to snackbar messages and tie them to the display of the
        #  message box
        self.hub.subscribe(self, SnackbarMessage,
                           handler=self._on_snackbar_message)

        # Internal cache so we don't have to keep calling get_object for the same Data.
        # Key should be (data_label, statistic) and value the translated object.
        self._get_object_cache = {}

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_subset_update_message)
        # These both call _on_layers_changed
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_subset_delete_message)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=self._on_subset_create_message)

        # Store for associations between Data entries:
        self._data_associations = self._init_data_associations()

        # Subscribe to messages that result in changes to the layers
        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_add_data_message)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_layers_changed)

        # Emit messages when icons are updated
        self.state.add_callback('viewer_icons',
                                lambda value: self.hub.broadcast(IconsUpdatedMessage('viewer', value, sender=self)))  # noqa
        self.state.add_callback('layer_icons',
                                lambda value: self.hub.broadcast(IconsUpdatedMessage('layer', value, sender=self)))  # noqa

    def _on_plugin_table_added(self, msg):
        if msg.plugin._plugin_name is None:
            # plugin was instantiated after the app was created, ignore
            return
        key = f"{msg.plugin._plugin_name}: {msg.table._table_name}"
        self._plugin_tables.setdefault(key, msg.table.user_api)

    def _iter_live_plugin_results(self, trigger_data_lbl=None, trigger_subset=None):
        trigger_subset_lbl = trigger_subset.label if trigger_subset is not None else None
        for data in self.data_collection:
            plugin_inputs = data.meta.get('_update_live_plugin_results', None)
            if plugin_inputs is None:
                continue
            data_subs = plugin_inputs.get('_subscriptions', {}).get('data', [])
            subset_subs = plugin_inputs.get('_subscriptions', {}).get('subset', [])
            if (trigger_data_lbl is not None and
                    not np.any([plugin_inputs.get(attr) == trigger_data_lbl
                                for attr in data_subs])):
                # trigger data does not match subscribed data entries
                continue
            if trigger_subset_lbl is not None:
                if not np.any([plugin_inputs.get(attr) == trigger_subset_lbl
                               for attr in subset_subs]):
                    # trigger subset does not match subscribed subsets
                    continue
                if not np.any([plugin_inputs.get(attr) == trigger_subset.data.label
                               for attr in data_subs]):
                    # trigger parent data of subset does not match subscribed data entries
                    continue
            yield (data, plugin_inputs)

    def _update_live_plugin_results(self, trigger_data_lbl=None, trigger_subset=None):
        for data, plugin_inputs in self._iter_live_plugin_results(trigger_data_lbl, trigger_subset):
            # update and overwrite data
            # make a new instance of the plugin to avoid changing any UI settings
            plg = self._jdaviz_helper.plugins.get(data.meta.get('Plugin'))._obj.new()
            if not plg.supports_auto_update:
                raise NotImplementedError(f"{data.meta.get('Plugin')} does not support live-updates")  # noqa
            plg.user_api.from_dict(plugin_inputs)
            # keep auto-updating, even if the option is hidden from the user API
            # (can remove this line if auto_update is exposed to the user API in the future)
            plg.add_results.auto_update_result = True
            try:
                plg()
            except Exception as e:
                self.hub.broadcast(SnackbarMessage(
                    f"Auto-update for {plugin_inputs['add_results']['label']} failed: {e}",
                    sender=self, color="error"))

    def _remove_live_plugin_results(self, trigger_data_lbl=None, trigger_subset=None):
        for data, plugin_inputs in self._iter_live_plugin_results(trigger_data_lbl, trigger_subset):
            self.hub.broadcast(SnackbarMessage(
                f"Removing {data.label} due to deletion of {trigger_subset.label if trigger_subset is not None else trigger_data_lbl}",  # noqa
                sender=self, color="warning"))
            self.data_item_remove(data.label)

    def _on_add_data_message(self, msg):
        self._on_layers_changed(msg)
        self._update_live_plugin_results(trigger_data_lbl=msg.data.label)

    def _on_subset_update_message(self, msg):
        # NOTE: print statements in here will require the viewer output_widget
        self._clear_object_cache(msg.subset.label)
        if msg.attribute == 'subset_state':
            self._update_live_plugin_results(trigger_subset=msg.subset)

    def _on_subset_delete_message(self, msg):
        self._remove_live_plugin_results(trigger_subset=msg.subset)
        if msg.subset.label in self._reserved_labels:
            # This might already be gone in test teardowns
            self._reserved_labels.remove(msg.subset.label)
        self._on_layers_changed(msg)

    def _on_subset_create_message(self, msg):
        self._reserved_labels.add(msg.subset.label)
        self._on_layers_changed(msg)

    def _on_plugin_plot_added(self, msg):
        if msg.plugin._plugin_name is None:
            # plugin was instantiated after the app was created, ignore
            return
        key = f"{msg.plugin._plugin_name}: {msg.plot._plot_name}"
        self._plugin_plots.setdefault(key, msg.plot.user_api)

    @property
    def hub(self):
        """
        Reference to the stored application handler `~glue.core.hub.Hub` instance
        for the application.
        """
        return self._application_handler.data_collection.hub

    @property
    def session(self):
        """
        Reference to the stored `~glue.core.session.Session` instance
        maintained by Glue for this application.
        """
        return self._application_handler.session

    @property
    def data_collection(self):
        """
        Reference to the stored `~glue.core.data_collection.DataCollection` instance,
        used to maintain the the data objects that been loaded into the application
        this session.
        """
        return self._application_handler.data_collection

    @property
    def verbosity(self):
        """
        Verbosity of the application for popup snackbars, choose from ``'debug'``,
        ``'info'``, ``'warning'`` (default), or ``'error'``.
        """
        return self._verbosity

    @verbosity.setter
    def verbosity(self, val):
        if val not in _verbosity_levels:
            raise ValueError(f'Invalid verbosity: {val}')
        self._verbosity = val

    @property
    def history_verbosity(self):
        """
        Verbosity of the logger history, choose from ``'debug'``, ``'info'`` (default),
        ``'warning'``, or ``'error'``.
        """
        return self._history_verbosity

    @history_verbosity.setter
    def history_verbosity(self, val):
        if val not in _verbosity_levels:
            raise ValueError(f'Invalid verbosity: {val}')
        self._history_verbosity = val

    def _add_style(self, path):
        """
        Appends an addition vue file containing a <style> tag that will be applied on top of the
        style defined in ``main_styles.vue``.  This is useful for config-specific or downstream
        styling at the app-level.

        Parameters
        ----------
        path : str or tuple
            Path to a ``.vue`` file containing style rules to inject into the app.
        """
        style_registry.add(path)

    def _on_snackbar_message(self, msg):
        """
        Displays a toast message with an editable message that be dismissed
        manually or will dismiss automatically after a timeout.

        Whether the message shows as a snackbar popup is controlled by ``self.verbosity``,
        whether the message is added to the history log is controlled by ``self.history_verbosity``.

        Parameters
        ----------
        msg : `~glue.core.SnackbarMessage`
            The Glue snackbar message containing information about displaying
            the message box.
        """
        # https://material-ui.com/customization/palette/ provides these options:
        #   success, info, warning, error, secondary, primary
        # We have these options:
        #   debug, info, warning, error
        # Therefore:
        # * debug is not used, it is more for the future if we also have a logger.
        # * info lets everything through
        # * success, secondary, and primary are treated as info (not sure what they are used for)
        # * None is also treated as info (when color is not set)
        popup_level = _verbosity_levels.index(self.verbosity)
        history_level = _verbosity_levels.index(self.history_verbosity)

        def _color_to_level(color):
            if color in _verbosity_levels:
                return color
            # could create dictionary mapping if we need anything more advanced
            return 'info'

        msg_level = _verbosity_levels.index(_color_to_level(msg.color))
        logger_plg = self._jdaviz_helper.plugins.get('Logger', None)
        self.state.snackbar_queue.put(self.state, logger_plg, msg,
                                      history=msg_level >= history_level,
                                      popup=msg_level >= popup_level)

    def _on_layers_changed(self, msg):
        if hasattr(msg, 'data'):
            layer_name = msg.data.label
            is_wcs_only = msg.data.meta.get(_wcs_only_label, False)
            is_not_child = self._get_assoc_data_parent(layer_name) is None
            children_layers = self._get_assoc_data_children(layer_name)

        elif hasattr(msg, 'subset'):
            # We don't need to reprocess the subset for every data collection entry
            if msg.subset.data != self.data_collection[0]:
                return
            layer_name = msg.subset.label
            is_wcs_only = False
            is_not_child = True
            children_layers = []
        else:
            raise NotImplementedError(f"cannot recognize new layer from {msg}")

        wcs_only_refdata_icon = ''  # blank - might be replaced with custom icon in the future
        # any changes here should also be manually reflected in orientation.vue
        orientation_icons = {'Default orientation': 'mdi-image-outline',
                             'North-up, East-left': 'nuel',
                             'North-up, East-right': 'nuer'}

        if layer_name not in self.state.layer_icons:
            if is_wcs_only:
                self.state.layer_icons = {**self.state.layer_icons,
                                          layer_name: orientation_icons.get(layer_name,
                                                                            wcs_only_refdata_icon)}
            elif not is_not_child:
                parent_icon = self.state.layer_icons.get(self._get_assoc_data_parent(layer_name))
                index = len([ln for ln, ic in self.state.layer_icons.items()
                             if not ic[:4] == 'mdi-' and
                             self._get_assoc_data_parent(ln) == parent_icon]) + 1
                self.state.layer_icons = {
                    **self.state.layer_icons,
                    layer_name: f"{parent_icon}{index}"
                }
            else:
                self.state.layer_icons = {
                    **self.state.layer_icons,
                    layer_name: alpha_index(len([ln for ln, ic in self.state.layer_icons.items()
                                                 if not ic[:4] == 'mdi-' and
                                                 self._get_assoc_data_parent(ln) is None]))
                }

        # all remaining layers at this point have a parent:
        child_layer_icons = {}
        for layer_name in self.state.layer_icons:
            children_layers = self._get_assoc_data_children(layer_name)
            if children_layers is not None:
                parent_icon = self.state.layer_icons[layer_name]
                for i, child_layer in enumerate(children_layers, start=1):
                    if child_layer not in self.state.layer_icons:
                        child_layer_icons[child_layer] = f'{parent_icon}{i}'

        if child_layer_icons:
            self.state.layer_icons = {
                **self.state.layer_icons,
                **child_layer_icons
            }

    def _change_reference_data(self, new_refdata_label, viewer_id=None):
        """
        Change reference data to Data with ``data_label``.
        This does not work on data without WCS.
        """
        if self.config not in ('imviz', 'deconfigged'):
            # this method is only meant for Imviz for now
            return

        if viewer_id is None:
            viewer = self._jdaviz_helper.default_viewer._obj
        else:
            viewer = self.get_viewer(viewer_id)

        old_refdata = viewer.state.reference_data

        if old_refdata is not None and ((new_refdata_label == old_refdata.label)
                                        or (old_refdata.coords is None)):
            # if there's no refdata change nor WCS, don't do anything:
            return

        if old_refdata is None:
            return

        # locate the central coordinate of old refdata in this viewer:
        sky_cen = viewer._get_center_skycoord()

        # estimate FOV in the viewer with old reference data:
        fov_sky_init = viewer._get_fov()

        new_refdata = self.data_collection[new_refdata_label]

        # make sure new refdata can be selected:
        refdata_choices = [choice.label for choice in viewer.state.ref_data_helper.choices]
        if new_refdata_label not in refdata_choices:
            viewer.state.ref_data_helper.append_data(new_refdata)
        if new_refdata_label not in [lyr.layer.label for lyr in viewer.layers]:
            viewer.add_data(new_refdata)
        viewer.state.ref_data_helper.refresh()

        # set the new reference data in the viewer:
        viewer.state.reference_data = new_refdata

        # also update the viewer item's reference data label:
        viewer_ref = viewer.reference
        viewer_item = self._get_viewer_item(viewer_ref)
        viewer_item['reference_data_label'] = new_refdata.label

        self.hub.broadcast(ChangeRefDataMessage(
            new_refdata,
            viewer,
            viewer_id=viewer.reference,
            old=old_refdata,
            sender=self))

        with delay_callback(viewer.state, 'x_min', 'x_max',
                            'y_min', 'y_max',
                            'zoom_center_x', 'zoom_center_y', 'zoom_radius'):
            if (
                all('_WCS_ONLY' in refdata.meta for refdata in [old_refdata, new_refdata]) and
                viewer.shape is not None
            ):
                # adjust zoom to account for new refdata if both the
                # old and new refdata are WCS-only layers
                # (which also ensures zoom_level is already determined):
                fov_sky_final = viewer._get_fov()
                viewer.zoom(
                    float(fov_sky_final / fov_sky_init)
                )

            # only re-center the viewer if all data layers have WCS:
            has_wcs_per_data = [data_has_valid_wcs(d) for d in viewer.data()]
            if all(has_wcs_per_data):
                # re-center the viewer on previous location.
                viewer.center_on(sky_cen)

    def _link_new_data(self, reference_data=None, data_to_be_linked=None):
        """
        When additional data is loaded, check to see if the spectral axis of
        any components are compatible with already loaded data. If so, link
        them so that they can be displayed on the same profile1D plot.
        """
        if self.config == 'imviz':  # Imviz does its own thing
            return
        elif not self.auto_link:
            return
        elif self.config == 'mosviz' and self.get_viewer('spectrum-viewer').state.reference_data:
            # Mosviz turns auto_link to False in order to batch
            # link the data after they have all been loaded.
            # It then reverts auto_link to True, which means that when
            # plugin data is added from mosviz, it can use the following line
            # to set reference data.
            reference_data = self.get_viewer('spectrum-viewer').state.reference_data.label

        dc = self.data_collection
        # This will need to be changed for cubeviz to support multiple cubes
        default_refdata_index = 0
        if self.config == 'mosviz':
            # In Mosviz, first data is always MOS Table. Use the next data
            default_refdata_index = 1
        elif self.config == 'cubeviz':
            spectral_axis_index = dc[0].meta['spectral_axis_index']
        ref_data = dc[reference_data] if reference_data else dc[default_refdata_index]
        linked_data = dc[data_to_be_linked] if data_to_be_linked else dc[-1]

        if 'Trace' in linked_data.meta:
            links = [LinkSame(linked_data.components[1], ref_data.components[0]),
                     LinkSame(linked_data.components[0], ref_data.components[1])]
            dc.add_link(links)
            return

        elif self.config == 'cubeviz' and linked_data.ndim == 1:
            # Don't want to use negative indices in case there are extra components like a mask
            ref_wavelength_component = dc[0].components[spectral_axis_index]
            # May need to update this for specutils 2
            linked_wavelength_component = linked_data.components[1]

            dc.add_link(LinkSame(ref_wavelength_component, linked_wavelength_component))
            return

        elif (linked_data.meta.get('Plugin', None) == '3D Spectral Extraction' or
                (linked_data.meta.get('Plugin', None) == ('Gaussian Smooth') and
                 linked_data.ndim < 3 and  # Cube linking requires special logic. See below
                 ref_data.ndim < 3)
              ):
            if self.config == 'specviz2d':
                links = []
                if linked_data.ndim == 2:
                    # extracted image added to data collection
                    ref_wavelength_component = ref_data.components[1]
                else:
                    # extracted spectrum added to data collection
                    ref_wavelength_component = ref_data.components[3]
                    links += [LinkSameWithUnits(linked_data.components[0], ref_data.components[1])]

                links += [LinkSameWithUnits(linked_data.components[0], ref_data.components[0]),
                          LinkSameWithUnits(linked_data.components[1], ref_wavelength_component)]
            else:
                links = [LinkSame(linked_data.components[0], ref_data.components[0]),
                         LinkSame(linked_data.components[1], ref_data.components[1])]

            dc.add_link(links)
            return

        # The glue-astronomy SpectralCoordinates currently seems incompatible with glue
        # WCSLink. This gets around it until there's an upstream fix. Also need to do this
        # for SpectralGWCS in 1D case (pixel linking below handles cubes)
        if (isinstance(linked_data.coords, SpectralCoordinates) or
                isinstance(linked_data.coords, SpectralGWCS) and linked_data.ndim == 1):
            wc_old = ref_data.world_component_ids[ref_data.meta['spectral_axis_index']]
            wc_new = linked_data.world_component_ids[linked_data.meta['spectral_axis_index']]
            self.data_collection.add_link(LinkSameWithUnits(wc_old, wc_new))
            return

        # NOTE: if Cubeviz ever supports multiple cubes, we might want to reintroduce WCS-linking
        # but will likely need affine approximation for performance

        pc_ref = [str(id).split(" ")[-1][1] for id in ref_data.pixel_component_ids]
        pc_linked = [str(id).split(" ")[-1][1] for id in linked_data.pixel_component_ids]

        links = []

        # This code loops through the returned locations of the x, y, and z
        # axes in the pixel_coordinate_ids of the reference data. It matches
        # the axes with the pixel_coordinate_ids of the linked data and links
        # those axes. There are special rules for linking 2D and 3D data, which
        # is as follows: 2D y to 3D z and 2D x to 3D y, and vice versa in the
        # case of moment map and collapse data because they need to be transposed.
        # See github comment:
        # https://github.com/spacetelescope/jdaviz/pull/1412#discussion_r907630682
        len_linked_pixel = len(linked_data.pixel_component_ids)

        for ind, pixel_coord in enumerate(pc_ref):
            ref_index = ind
            if (len_linked_pixel == 2 and
                    (linked_data.meta.get("Plugin", None) in
                     ['Moment Maps', 'Collapse', 'Sonify Data'])):

                if spectral_axis_index in (2, -1):
                    link_to_x = 'z'
                elif spectral_axis_index == 0:
                    link_to_x = 'x'

                if pixel_coord == link_to_x:
                    linked_index = pc_linked.index('x')
                elif pixel_coord == 'y':
                    linked_index = pc_linked.index('y')
                else:
                    continue
            elif len_linked_pixel == 2:
                if pixel_coord == 'z':
                    linked_index = pc_linked.index('y')
                elif pixel_coord == 'y':
                    linked_index = pc_linked.index('x')
                else:
                    continue
            elif pixel_coord in pc_linked:
                linked_index = pc_linked.index(pixel_coord)
            else:
                continue

            links.append(LinkSameWithUnits(ref_data.pixel_component_ids[ref_index],
                                           linked_data.pixel_component_ids[linked_index]))

        dc.add_link(links)

    def load_data(self, file_obj, parser_reference=None, **kwargs):
        """
        Provided a path to a data file, open and parse the data into the
        `~glue.core.data_collection.DataCollection` for this session.

        For some parsers, this also attempts to find WCS links that exist
        between data components.

        Parameters
        ----------
        file_obj : str or file-like
            File object for the data to be loaded.

        parser_reference : str or `None`
            The actual data parser to use. It must already be registered
            to glue's data parser registry. This is mainly for internal use.

        **kwargs : dict
            Additional keywords to be passed into the parser defined by
            ``parser_reference``.

        """
        self.loading = True
        try:
            if isinstance(file_obj, pathlib.Path):
                file_obj = str(file_obj)

            # attempt to get a data parser from the config settings
            parser = None
            data = self.state.settings.get('data', None)
            if parser_reference:
                parser = data_parser_registry.members.get(parser_reference)
            elif data and isinstance(data, dict):
                data_parser = data.get('parser', None)
                if data_parser:
                    parser = data_parser_registry.members.get(data_parser)

            if parser is not None:
                parser(self, file_obj, **kwargs)
            else:
                self._application_handler.load_data(file_obj)

        except Exception:  # Reset state on uncaught errors
            cfg_name = self.state.settings.get('configuration', 'unknown')
            if cfg_name in ('mosviz', ):  # Add more as needed.
                self.data_collection.clear()
            raise
        finally:
            self.loading = False

    def get_viewer(self, viewer_reference):
        """
        Return a `~glue_jupyter.bqplot.common.BqplotBaseView` viewer instance.
        This is *not* an ``IPyWidget``. This is stored here because
        the state of the viewer and data methods that allow add/removing data
        to the viewer exist in a wrapper around the core ``IPyWidget``, which
        is needed to interact with the data rendered within a viewer.

        Notes
        -----
        If viewer does not have a reference, it is going to try to look
        up the viewer using the given reference as ID.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the YAML configuration file.

        Returns
        -------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        return self._viewer_by_reference(viewer_reference, fallback_to_id=True)

    def get_viewer_by_id(self, vid):
        """Like :meth:`get_viewer` but use ID directly instead of reference name.
        This is useful when reference name is `None`.
        """
        return self._viewer_store.get(vid)

    def _get_wcs_from_subset(self, subset_state, data=None):
        """ Usually WCS is subset.parent.coords, except special cubeviz case."""
        parent_data = subset_state.attributes[0].parent if not data else self.data_collection[data]

        # 3D WCS is not yet supported so this workaround allows SkyRegions to
        # be returned for data in cubeviz
        if self.config == 'cubeviz':
            wcs = parent_data.meta.get("_orig_spatial_wcs", None)
        else:
            if not hasattr(parent_data, 'coords'):
                raise AttributeError(f'{parent_data} does not have anything set for'
                                     f'the coords attribute, unable to extract WCS')
            wcs = parent_data.coords
        return wcs

    def get_subsets(self, subset_name=None, spectral_only=False,
                    spatial_only=False, object_only=False,
                    simplify_spectral=True, use_display_units=False,
                    include_sky_region=False, wrt_data=None):
        """
        Returns all branches of glue subset tree in the form that subset plugin
        can recognize.

        Parameters
        ----------
        subset_name : str
            The subset name.
        spectral_only : bool
            Return only spectral subsets.
        spatial_only : bool
            Return only spatial subsets, except masked subsets (uncommon).
        object_only : bool
            Return only object relevant information and
            leave out the region class name and glue_state.
        simplify_spectral : bool
            Return a composite spectral subset collapsed to a simplified
            SpectralRegion.
        use_display_units : bool, optional
            Whether to convert to the display units defined in the
            :ref:`Unit Conversion <unit-conversion>` plugin.
        include_sky_region : bool
            If True, for spatial subsets that have a WCS associated with their
            parent data, return a sky region in addition to pixel region. If
            subset is composite, a sky region for each constituent subset will
            be returned.
        wrt_data : str or None
            Name of data to use for applying WCS to subset when returning as
            a sky region object.

        Returns
        -------
        data : dict
            Returns a nested dictionary with, for each subset, 'name', 'glue_state',
            'region', 'sky_region' (set to None if not applicable), and 'subset_state'.
            If subset is composite, each constituant subset will be included individually.
        """

        dc = self.data_collection
        subsets = dc.subset_groups

        all_subsets = {}

        # If we only want one subset, no need to loop through them all
        if subset_name not in (None, ""):
            if isinstance(subset_name, str):
                subsets = [subset for subset in subsets if subset.label == subset_name]
                if subsets == []:
                    all_labels = sorted(sg.label for sg in dc.subset_groups)
                    raise ValueError(f"{subset_name} not in {all_labels}")
            else:
                raise ValueError("subset_name must be a string.")

        for subset in subsets:

            label = subset.label

            if isinstance(subset.subset_state, CompositeSubsetState):
                # Region composed of multiple ROI or Range subset
                # objects that must be traversed
                subset_region = self.get_sub_regions(subset.subset_state,
                                                     simplify_spectral, use_display_units,
                                                     get_sky_regions=include_sky_region,
                                                     wrt_data=wrt_data)

            elif isinstance(subset.subset_state, RoiSubsetState):
                subset_region = self._get_roi_subset_definition(subset.subset_state,
                                                                to_sky=include_sky_region,
                                                                wrt_data=wrt_data)

            elif isinstance(subset.subset_state, RangeSubsetState):
                # 2D regions represented as SpectralRegion objects
                subset_region = self._get_range_subset_bounds(subset.subset_state,
                                                              simplify_spectral,
                                                              use_display_units)

            elif isinstance(subset.subset_state, MultiMaskSubsetState):
                subset_region = self._get_multi_mask_subset_definition(subset.subset_state)

            else:
                # subset.subset_state can be an instance of something else
                # we do not know how to handle yet
                all_subsets[label] = [{"name": subset.subset_state.__class__.__name__,
                                       "glue_state": subset.subset_state.__class__.__name__,
                                       "region": None,
                                       "sky_region": None,
                                       "subset_state": subset.subset_state}]
                continue

            # Is the subset spectral, spatial, temporal?
            is_spectral = self._is_subset_spectral(subset_region)
            is_temporal = self._is_subset_temporal(subset_region)

            # Remove duplicate spectral regions
            if is_spectral and isinstance(subset_region, SpectralRegion):
                subset_region = self._remove_duplicate_bounds(subset_region)

            if spectral_only and is_spectral:
                if object_only and not simplify_spectral:
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region
            elif spatial_only and not is_spectral:
                if object_only:
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region
            elif not spectral_only and not spatial_only:
                # General else statement if no type was specified
                if object_only and not isinstance(subset_region, SpectralRegion):
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region

            if not (spectral_only or spatial_only) and is_temporal:
                if object_only:
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region

        if subset_name:
            return all_subsets[subset_name]
        else:
            return all_subsets

    def _is_subset_spectral(self, subset_region):
        if isinstance(subset_region, SpectralRegion):
            return True
        elif isinstance(subset_region, list) and len(subset_region) > 0:
            if isinstance(subset_region[0]['region'], SpectralRegion):
                return True
        return False

    def _is_subset_temporal(self, subset_region):
        if isinstance(subset_region, Time):
            return True
        elif isinstance(subset_region, list):
            if isinstance(subset_region[0]['region'], Time):
                return True
        return False

    def _remove_duplicate_bounds(self, spec_regions):
        regions_no_dups = None

        for region in spec_regions:
            if not regions_no_dups:
                regions_no_dups = region
            elif region.bounds not in regions_no_dups.subregions:
                regions_no_dups += region
        return regions_no_dups

    def _get_range_subset_bounds(self, subset_state,
                                 simplify_spectral=True, use_display_units=False):
        # TODO: Use global display units
        # units = dc[0].data.coords.spectral_axis.unit
        if not hasattr(subset_state.att, "parent"):  # e.g., Cubeviz
            viewer = self.get_viewer(self._jdaviz_helper._default_spectrum_viewer_reference_name)
            data = viewer.data()
            if data and len(data) > 0 and isinstance(data[0], Spectrum):
                units = data[0].spectral_axis.unit
            else:
                raise ValueError("Unable to find spectral axis units")
        else:
            data = subset_state.att.parent
            ndim = data.get_component("flux").ndim
            if ndim == 2:
                units = u.pix
            else:
                handler, _ = data_translator.get_handler_for(Spectrum)
                spec = handler.to_object(data)
                units = spec.spectral_axis.unit

        if use_display_units and units != u.pix:
            # converting may result in flipping order (wavelength <-> frequency)
            ret_units = self._get_display_unit('spectral')
            subset_bounds = [(subset_state.lo * units).to(ret_units, u.spectral()),
                             (subset_state.hi * units).to(ret_units, u.spectral())]
            spec_region = SpectralRegion(min(subset_bounds), max(subset_bounds))
        else:
            spec_region = SpectralRegion(subset_state.lo * units, subset_state.hi * units)

        if not simplify_spectral:
            return [{"name": subset_state.__class__.__name__,
                     "glue_state": subset_state.__class__.__name__,
                     "region": spec_region,
                     "sky_region": None,  # not implemented for spectral, include for consistancy
                     "subset_state": subset_state}]
        return spec_region

    def _get_multi_mask_subset_definition(self, subset_state):

        return [{"name": subset_state.__class__.__name__,
                 "glue_state": subset_state.__class__.__name__,
                 "region": subset_state.total_masked_first_data(),
                 "sky_region": None,
                 "subset_state": subset_state}]

    def _get_roi_subset_definition(self, subset_state, to_sky=False, wrt_data=None):
        wcs = None
        # If SkyRegion is explicitly requested or the user has specified something for
        # wrt_data, this will be true
        if to_sky or wrt_data is not None:
            wcs = self._get_wcs_from_subset(subset_state, data=wrt_data)

        # if no spatial wcs on subset, we have to skip computing sky region for this subset
        # but want to do so without raising an error (since many subsets could be requested)
        roi_as_sky_region = None
        if wcs is not None:
            if self.config == 'cubeviz':
                # the value for wcs returned above will be in 2D dimensions, which is needed
                # for this translation to work
                roi_as_sky_region = roi_subset_state_to_region(subset_state).to_sky(wcs)
            else:
                roi_as_sky_region = roi_subset_state_to_region(subset_state, to_sky=True)

            roi_as_region = roi_as_sky_region.to_pixel(wcs)
        else:
            # pixel region
            roi_as_region = roi_subset_state_to_region(subset_state)

        return [{"name": subset_state.roi.__class__.__name__,
                 "glue_state": subset_state.__class__.__name__,
                 "region": roi_as_region,
                 "sky_region": roi_as_sky_region,
                 "subset_state": subset_state}]

    def get_sub_regions(self, subset_state, simplify_spectral=True,
                        use_display_units=False, get_sky_regions=False,
                        wrt_data=None):

        if isinstance(subset_state, CompositeSubsetState):
            if subset_state and hasattr(subset_state, "state2") and subset_state.state2:
                one = self.get_sub_regions(subset_state.state1,
                                           simplify_spectral, use_display_units,
                                           get_sky_regions=get_sky_regions,
                                           wrt_data=wrt_data)
                two = self.get_sub_regions(subset_state.state2,
                                           simplify_spectral, use_display_units,
                                           get_sky_regions=get_sky_regions,
                                           wrt_data=wrt_data)
                if simplify_spectral and isinstance(two, SpectralRegion):
                    merge_func = self._merge_overlapping_spectral_regions_worker
                else:
                    def merge_func(spectral_region):  # noop
                        return spectral_region

                if isinstance(one, list) and "glue_state" in one[0]:
                    one[0]["glue_state"] = subset_state.__class__.__name__

                if (isinstance(one, list)
                        and isinstance(one[0]["subset_state"], MultiMaskSubsetState)
                        and simplify_spectral):
                    return two
                elif (isinstance(two, list)
                        and isinstance(two[0]["subset_state"], MultiMaskSubsetState)
                        and simplify_spectral):
                    return one

                if isinstance(subset_state.state2, InvertState):
                    # This covers the REMOVE subset mode

                    # As an example for how this works:
                    # a = SpectralRegion(4 * u.um, 7 * u.um) + SpectralRegion(9 * u.um, 11 * u.um)
                    # b = SpectralRegion(5 * u.um, 6 * u.um)
                    # After running the following code with a as one and b as two:
                    # Spectral Region, 3 sub-regions:
                    #   (4.0 um, 5.0 um)    (6.0 um, 7.0 um)    (9.0 um, 11.0 um)
                    if isinstance(two, SpectralRegion):
                        new_spec = None
                        for sub in one:
                            if not new_spec:
                                new_spec = two.invert(sub.lower, sub.upper)
                            else:
                                new_spec += two.invert(sub.lower, sub.upper)
                        return new_spec
                    else:
                        if isinstance(two, list):
                            two[0]['glue_state'] = "AndNotState"
                        return merge_func(one + two)
                elif subset_state.op is operator.and_:
                    # This covers the AND subset mode

                    # Example of how this works with "one" being the AND region
                    # and "two" being two Range subsets connected by an OR state:
                    # one = SpectralRegion(4.5 * u.um, 7.5 * u.um)
                    # two = SpectralRegion(4 * u.um, 5 * u.um) + SpectralRegion(7 * u.um, 8 * u.um)
                    #
                    # oppo = two.invert(one.lower, one.upper)
                    # Spectral Region, 1 sub-regions:
                    #   (5.0 um, 7.0 um)
                    #
                    # oppo.invert(one.lower, one.upper)
                    # Spectral Region, 2 sub-regions:
                    #   (4.5 um, 5.0 um)   (7.0 um, 7.5 um)
                    if isinstance(two, SpectralRegion):
                        # Taking an AND state of an empty region is allowed
                        # but there is no way for SpectralRegion to display that information.
                        # Instead, we raise a ValueError
                        if one.upper.value < two.lower.value or one.lower.value > two.upper.value:
                            raise ValueError("AND mode should overlap with existing subset")
                        oppo = two.invert(one.lower, one.upper)

                        return oppo.invert(one.lower, one.upper)
                    else:
                        return merge_func(two + one)
                elif subset_state.op is operator.or_:
                    # This covers the ADD subset mode
                    # one + two works for both Range and ROI subsets
                    if one and two:
                        return merge_func(two + one)
                    elif one:
                        return one
                    elif two:
                        return two
                elif subset_state.op is operator.xor:
                    # This covers the XOR subset mode

                    # Example of how this works, with "one" acting
                    # as the XOR region and "two" as two ranges joined
                    # by an OR:
                    # a = SpectralRegion(4 * u.um, 5 * u.um)
                    # b = SpectralRegion(6 * u.um, 9 * u.um)
                    #
                    # one = SpectralRegion(4.5 * u.um, 12 * u.um)
                    # two = a + b

                    # two.invert(one.lower, one.upper)
                    # Spectral Region, 2 sub-regions:
                    #   (5.0 um, 6.0 um)    (9.0 um, 12.0 um)

                    # one.invert(two.lower, two.upper)
                    # Spectral Region, 1 sub-regions:
                    #   (4.0 um, 4.5 um)

                    # two.invert(one.lower, one.upper) + one.invert(two.lower, two.upper)
                    # Spectral Region, 3 sub-regions:
                    #   (4.0 um, 4.5 um)    (5.0 um, 6.0 um)    (9.0 um, 12.0 um)

                    if isinstance(two, SpectralRegion):
                        # This is the main application of XOR to other regions
                        if one.lower > two.lower and one.upper < two.upper:
                            if len(two) < 2:
                                inverted_region = one.invert(two.lower, two.upper)
                            else:
                                two_2 = None
                                for subregion in two:
                                    temp_region = None
                                    # No overlap
                                    if subregion.lower > one.upper or subregion.upper < one.lower:
                                        continue
                                    temp_lo = max(subregion.lower, one.lower)
                                    temp_hi = min(subregion.upper, one.upper)
                                    temp_region = SpectralRegion(temp_lo, temp_hi)
                                    if two_2:
                                        two_2 += temp_region
                                    else:
                                        two_2 = temp_region
                                inverted_region = two_2.invert(one.lower, one.upper)
                        else:
                            inverted_region = two.invert(one.lower, one.upper)

                        new_region = None
                        for subregion in two:
                            temp_region = None
                            # Add all subregions that do not intersect with XOR region
                            # to a new SpectralRegion object
                            if subregion.lower > one.upper or subregion.upper < one.lower:
                                temp_region = subregion
                            # Partial overlap
                            elif subregion.lower < one.lower and subregion.upper < one.upper:
                                temp_region = SpectralRegion(subregion.lower, one.lower)
                            elif subregion.upper > one.upper and subregion.lower > one.lower:
                                temp_region = SpectralRegion(one.upper, subregion.upper)

                            if not temp_region:
                                continue

                            if new_region:
                                new_region += temp_region
                            else:
                                new_region = temp_region

                        # This adds the edge regions that are otherwise not included
                        if new_region:
                            return merge_func(new_region + inverted_region)
                        return inverted_region
                    else:
                        return merge_func(two + one)
            else:
                # This gets triggered in the InvertState case where state1
                # is an object and state2 is None
                return self.get_sub_regions(subset_state.state1,
                                            simplify_spectral,
                                            use_display_units,
                                            get_sky_regions=get_sky_regions,
                                            wrt_data=wrt_data)
        elif subset_state is not None:
            # This is the leaf node of the glue subset state tree where
            # a subset_state is either ROI, Range, or MultiMask.
            if isinstance(subset_state, RoiSubsetState):
                return self._get_roi_subset_definition(subset_state, to_sky=get_sky_regions,
                                                       wrt_data=wrt_data)

            elif isinstance(subset_state, RangeSubsetState):
                return self._get_range_subset_bounds(subset_state,
                                                     simplify_spectral, use_display_units)
            elif isinstance(subset_state, MultiMaskSubsetState):
                return self._get_multi_mask_subset_definition(subset_state)

    def delete_subsets(self, subset_labels=None):
        """
        Delete all or specified subsets in app.

        This method removes subsets based on the provided ``subset_labels`` (a
        single subset label or multiple labels). If ``subset_labels``
        is None (default), all subsets will be removed.

        Parameters
        ----------
        subset_labels : str or list of str or None
            The label(s) of the subsets to delete. If None, all subsets will be
            removed.
        """

        # delete all subsets
        if subset_labels is None:
            for subset_group in self.data_collection.subset_groups:
                self.data_collection.remove_subset_group(subset_group)

        else:
            if isinstance(subset_labels, str):
                subset_labels = [subset_labels]
            labels = np.asarray(subset_labels)
            sg = self.data_collection.subset_groups
            subset_grp_labels = {s.label: s for s in sg}

            # raise ValueError if any subset in 'subset_labels' isn't actually
            # in the data collection, before deleting subsets
            invalid_labels = ~np.isin(labels, list(subset_grp_labels.keys()))
            if np.any(invalid_labels):
                bad = ', '.join([x for x in labels[invalid_labels]])
                raise ValueError(f'{bad} not in data collection, can not delete.')
            else:
                for label in labels:
                    self.data_collection.remove_subset_group(subset_grp_labels[label])

    def _get_display_unit(self, axis):
        if self._jdaviz_helper is None:
            # cannot access either the plugin or the spectrum viewer.
            # Plugins that access the unit at this point will need to
            # detect that they are set to unitless and attempt again later.
            return ''

        try:
            uc = self.get_tray_item_from_name('g-unit-conversion')  # even if not relevant
        except KeyError:
            # UC plugin not available (should only be for: imviz, mosviz)
            uc = None
        if uc is None:  # noqa
            # fallback on native units (unit conversion is not enabled)
            if hasattr(self._jdaviz_helper, '_default_spectrum_viewer_reference_name'):
                viewer_name = self._jdaviz_helper._default_spectrum_viewer_reference_name
            elif hasattr(self._jdaviz_helper, '_default_spectrum_2d_viewer_reference_name'):
                viewer_name = self._jdaviz_helper._default_spectrum_2d_viewer_reference_name
            elif axis == 'temporal':
                # No unit for ramp's time (group/resultant) axis:
                return None
            else:
                raise NotImplementedError("No default viewer reference found.")
            if axis == 'spectral':
                sv = self.get_viewer(viewer_name)
                return sv.data()[0].spectral_axis.unit
            elif axis in ('flux', 'sb', 'spectral_y'):
                sv = self.get_viewer(viewer_name)
                sv_y_unit = sv.data()[0].flux.unit
                if axis == 'spectral_y':
                    return sv_y_unit
                # since this is where we're falling back on native units (UC plugin might not exist)
                # first check the spectrum viewer y axis for any solid angle unit (i think that it
                # will ALWAYS be in flux, but just to be sure). If no solid angle unit is found,
                # check the flux viewer for surface brightness units
                sv_y_angle_unit = check_if_unit_is_per_solid_angle(sv_y_unit, return_unit=True)

                # check flux viewer if none in spectral viewer
                fv_angle_unit = None
                if not sv_y_angle_unit:
                    if hasattr(self._jdaviz_helper, '_default_flux_viewer_reference_name'):
                        vname = self._jdaviz_helper._default_flux_viewer_reference_name
                        fv = self.get_viewer(vname)
                        fv_unit = fv.data()[0].get_object().flux.unit
                        fv_angle_unit = check_if_unit_is_per_solid_angle(fv_unit,
                                                                         return_unit=True)
                    else:
                        # mosviz, not sure what to do here but can't access flux
                        # viewer the same way. once we force the UC plugin to
                        # exist this won't matter anyway because units can be
                        # acessed from the plugin directly. assume u.sr for now
                        fv_angle_unit = u.sr

                solid_angle_unit = sv_y_angle_unit or fv_angle_unit

                if axis == 'flux':
                    if sv_y_angle_unit:
                        return sv_y_unit * solid_angle_unit
                    return sv_y_unit
                elif axis == 'sb':
                    if sv_y_angle_unit:
                        return sv_y_unit
                    return sv_y_unit / solid_angle_unit
            else:
                raise ValueError(f"could not find units for axis='{axis}'")
        if axis == 'spectral_y':
            return uc.spectral_y_unit
        try:
            return getattr(uc, f'{axis}_unit_selected')
        except AttributeError:
            raise ValueError(f"could not find display unit for axis='{axis}'")

    def simplify_spectral_subset(self, subset_name, att, overwrite=False):
        """
        Convert a composite spectral subset consisting of And, AndNot, Or, Replace, and Xor
        into one consisting of just Range and Or state objects.

        Parameters
        ----------
        subset_name : str
            Name of subset to simplify.
        att : str
            Attribute that the subset uses to apply to data.
        overwrite : bool
            Whether to update the current subset with the simplified state or apply it
            to a new subset.
        """
        if self.is_there_overlap_spectral_subset(subset_name):
            new_state = self.merge_overlapping_spectral_regions(subset_name, att)
        else:
            new_state = None
            spectral_region = self.get_subsets(subset_name, spectral_only=True)
            # Reverse through sub regions so that they are added back
            # in the order of lowest values to highest
            for index in range(len(spectral_region) - 1, -1, -1):
                convert_to_range = RangeSubsetState(spectral_region[index].lower.value,
                                                    spectral_region[index].upper.value,
                                                    att)
                if new_state is None:
                    new_state = convert_to_range
                else:
                    new_state = new_state | convert_to_range

        dc = self.data_collection
        if not overwrite:
            dc.new_subset_group(subset_state=new_state)
        else:
            old_subset = [subsets for subsets in dc.subset_groups
                          if subsets.label == subset_name][0]
            old_subset.subset_state = new_state

    def is_there_overlap_spectral_subset(self, subset_name):
        """
        Returns True if the spectral subset with subset_name has overlapping
        subregions.
        """
        spectral_region = self.get_subsets(subset_name, simplify_spectral=False, spectral_only=True)
        n_reg = len(spectral_region)
        if not spectral_region or n_reg < 2:
            return False
        for index in range(n_reg - 1):
            if spectral_region[index]['region'].upper.value >= spectral_region[index + 1]['region'].lower.value:  # noqa: E501
                return True
        return False

    @staticmethod
    def _merge_overlapping_spectral_regions_worker(spectral_region):
        if len(spectral_region) < 2:  # noop
            return spectral_region

        merged_regions = spectral_region[0]  # Instantiate merged regions
        for cur_reg in spectral_region[1:]:
            # If the lower value of the current subregion is less than or equal to the upper
            # value of the last subregion added to merged_regions, update last region in
            # merged_regions with the max upper value between the two regions.
            if cur_reg.lower <= merged_regions.upper:
                merged_regions._subregions[-1] = (
                    merged_regions._subregions[-1][0],
                    max(cur_reg.upper, merged_regions._subregions[-1][1]))
            else:
                merged_regions += cur_reg
        return merged_regions

    def merge_overlapping_spectral_regions(self, subset_name, att):
        """
        Takes a spectral subset with subset_name and returns an ``OrState`` object
        that merges all overlapping subregions.

        Parameters
        ----------
        subset_name : str
            Name of subset to simplify.
        att : str
            Attribute that the subset uses to apply to data.
        """
        merged_regions = self.get_subsets(subset_name, spectral_only=True)

        new_state = None
        for region in reversed(merged_regions):
            convert_to_range = RangeSubsetState(region.lower.value, region.upper.value, att)
            if new_state:
                new_state = new_state | convert_to_range
            else:
                new_state = convert_to_range

        return new_state

    def add_data(self, data, data_label=None, notify_done=True, parent=None):
        """
        Add data to the Glue ``DataCollection``.

        Parameters
        ----------
        data : any
            Data to be stored in the ``DataCollection``. This must either be
            a `~glue.core.data.Data` instance, or an arbitrary data instance
            for which there exists data translation functions in the
            glue astronomy repository.
        data_label : str, optional
            The name associated with this data. If none is given, label is pulled
            from the input data (if `~glue.core.data.Data`) or a generic name is
            generated.
        notify_done : bool
            Flag controlling whether a snackbar message is set when the data is
            added to the app. Set to False to avoid overwhelming the user if
            lots of data is getting loaded at once.
        parent : str, optional
            Associate the added Data entry as the child of layer ``parent``.
        """

        if not data_label and hasattr(data, "label"):
            data_label = data.label
        data_label = self.return_unique_name(data_label)
        if data_label in self.data_collection.labels:
            warnings.warn(f"Overwriting existing data entry with label '{data_label}'")

        self.data_collection[data_label] = data

        # manage associated Data entries:
        self._add_assoc_data_as_parent(data_label)
        if parent is not None:
            data_collection_labels = [data.label for data in self.data_collection]
            if parent not in data_collection_labels:
                raise ValueError(f'parent "{parent}" is not a valid data label in '
                                 f'the data collection: {data_collection_labels}.')

            # Does the parent Data have a parent? If so, raise error:
            parent_of_parent = self._get_assoc_data_parent(parent)
            if parent_of_parent is not None:
                raise NotImplementedError('Data associations are currently supported '
                                          'between root layers (without parents) and their '
                                          f'children, but the proposed parent "{parent}" has '
                                          f'parent "{parent_of_parent}".')
            self._set_assoc_data_as_child(data_label, new_parent_label=parent)

        # Send out a toast message
        if notify_done:
            snackbar_message = SnackbarMessage(
                f"Data '{data_label}' successfully added.", sender=self, color="success")
            self.hub.broadcast(snackbar_message)

    def return_data_label(self, loaded_object, ext=None, alt_name=None, check_unique=True):
        """
        Returns a unique data label that can be safely used to load data into data collection.

        Parameters
        ----------
        loaded_object : str or object
            The path to a data file or FITS HDUList or image object or Spectrum or
            NDData array or numpy.ndarray.
        ext : str, optional
            The extension (or other distinguishing feature) of data used to identify it.
            For example, "filename[FLUX]" where "FLUX" is the ext value.
        alt_name : str, optional
            Alternate names that can be used if none of the options provided are valid.
        check_unique : bool
            Included so that this method can be used with data label retrieval in addition
            to generation.

        Returns
        -------
        data_label : str
            A unique data label that at its root is either given by the user at load time
            or created by Jdaviz using a description of the loaded filetype.
        """
        data_label = None

        if loaded_object is None:
            pass
        elif isinstance(loaded_object, str):
            # This is either the full file path or the basename or the user input data label
            if loaded_object.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_format = loaded_object.lower().split(".")[-1]
                loaded_object = os.path.splitext(os.path.basename(loaded_object))[0]
                data_label = f"{loaded_object}[{file_format}]"
            elif os.path.isfile(loaded_object) or os.path.isdir(loaded_object):
                # File that is not an image file
                data_label = os.path.splitext(os.path.basename(loaded_object))[0]
            else:
                # Not a file path so assumed to be a data label
                data_label = loaded_object
        elif isinstance(loaded_object, fits.hdu.hdulist.HDUList):
            if hasattr(loaded_object, 'file_name'):
                data_label = f"{loaded_object.file_name}[HDU object]"
            else:
                data_label = "Unknown HDU object"
        elif isinstance(loaded_object, Spectrum):
            data_label = "Spectrum"
        elif isinstance(loaded_object, NDData):
            data_label = "NDData"
        elif isinstance(loaded_object, np.ndarray):
            data_label = "Array"

        if data_label is None and alt_name is not None and isinstance(alt_name, str):
            data_label = alt_name
        elif data_label is None:
            data_label = "Unknown"

        if check_unique:
            data_label = self.return_unique_name(data_label, ext=ext)

        return data_label

    def return_unique_name(self, label, typ='data', ext=None):
        if typ == 'data':
            exist_labels = self.data_collection.labels
        elif typ == 'viewer':
            exist_labels = list(self._viewer_store.keys())
        elif isinstance(typ, list):
            exist_labels = typ
        else:
            raise ValueError("typ must be either 'data', 'viewer', or a list of strings")
        if label is None:
            label = "Unknown"

        # This regex checks for any length of characters that end
        # with a space followed by parenthesis with a number inside.
        # If there is a match, the space and parenthesis section will be
        # removed so that the remainder of the label can be checked
        # against the label.
        check_if_dup = re.compile(r"(.*)(\s\(\d*\))$")
        number_of_duplicates = 0
        max_number = 0
        for exist_label in exist_labels:
            # If label is a duplicate of another label
            if re.fullmatch(check_if_dup, exist_label):
                exist_label_split = exist_label.split(" ")
                exist_label_without_dup = " ".join(exist_label_split[:-1])
                exist_label = exist_label_without_dup
                # Remove parentheses and cast to float
                number_dup = int(exist_label_split[-1][1:-1])
                # Used to keep track the max number of duplicates,
                # even if not all duplicates are loaded (or some
                # are renamed)
                if number_dup > max_number:
                    max_number = number_dup

            if ext and f"{label}[{ext}]" == exist_label:
                number_of_duplicates += 1
            elif ext is None and label == exist_label:
                number_of_duplicates += 1

        if ext:
            label = f"{label}[{ext}]"

        if number_of_duplicates > 0:
            label = f"{label} ({number_of_duplicates})"

        # It is possible to add data named "test (1)" and then
        # add another data named "test" and return_unique_name will see the
        # first test and assume the second is the duplicate, appending
        # "(1)" to the end. This overwrites the original data and
        # causes issues. This block alters the duplicate number to be something unique
        # (one more than the max number duplicate found)
        # if a duplicate is still found in data_collection.
        if label in exist_labels:
            label_split = label.split(" ")
            label_without_dup = " ".join(label_split[:-1])
            label = f"{label_without_dup} ({max_number + 1})"

        return label

    def add_data_to_viewer(self, viewer_reference, data_label,
                           visible=True, clear_other_data=False):
        """
        Plots a data set from the data collection in the specific viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        visible : bool
            Whether the layer should be initialized as visibile.
        clear_other_data : bool
            Removes all other currently plotted data and only shows the newly
            defined data set.
        """
        if ('mosviz_row' in self.state.settings and
            not (self.get_viewer(
                self._jdaviz_helper._default_table_viewer_reference_name
            ).row_selection_in_progress) and
            self.data_collection[data_label].meta['mosviz_row'] !=
                self.state.settings['mosviz_row']):
            raise NotImplementedError("Intra-row plotting not supported. "
                                      "Please use the table viewer to change rows")

        viewer_item = self._get_viewer_item(viewer_reference)
        if viewer_item is None:
            raise ValueError(f"Could not identify viewer with reference {viewer_reference}")

        self.set_data_visibility(viewer_item, data_label, visible=visible, replace=clear_other_data)

    def remove_data_from_viewer(self, viewer_reference, data_label):
        """
        Removes a data set from the specified viewer.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        """
        viewer_item = self._get_viewer_item(viewer_reference)
        viewer_id = viewer_item['id']
        viewer = self.get_viewer_by_id(viewer_id)

        [data] = [x for x in self.data_collection if x.label == data_label]

        viewer.remove_data(data)
        viewer._layers_with_defaults_applied = [layer_info for layer_info in viewer._layers_with_defaults_applied  # noqa
                                                if layer_info['data_label'] != data.label]  # noqa

        remove_data_message = RemoveDataMessage(data, viewer,
                                                viewer_id=viewer_id,
                                                sender=self)
        self.hub.broadcast(remove_data_message)

    def _data_id_from_label(self, label):
        """
        Retrieve the data item given the Glue ``DataCollection`` data label.

        Parameters
        ----------
        label : str
            Label associated with the ``DataCollection`` item. This is also the
            name shown in the data list.

        Returns
        -------
        dict
            The data item dictionary containing the id and name of the given
            data set.
        """
        for data_item in self.state.data_items:
            if data_item['name'] == label:
                return data_item['id']

    def get_viewer_ids(self, prefix=None):
        """Return a list of available viewer IDs.

        Parameters
        ----------
        prefix : str or `None`
            If not `None`, only return viewer IDs with given prefix
            (case-sensitive). Otherwise, all viewer IDs are returned.

        Returns
        -------
        vids : list of str
            Sorted list of viewer IDs.

        """
        all_keys = sorted(self._viewer_store.keys())

        if isinstance(prefix, str):
            vids = [k for k in all_keys if k.startswith(prefix)]
        else:
            vids = all_keys

        return vids

    def get_viewer_reference_names(self):
        """Return a list of available viewer reference names."""
        # Cannot sort because of None
        return [self._viewer_item_by_id(vid).get('reference') for vid in self._viewer_store]

    def get_viewers_of_cls(self, cls):
        """Return a list of viewers of a specific class."""
        if isinstance(cls, str):
            cls_name = cls
        else:
            cls_name = cls.__name__
        return [viewer for viewer in self._viewer_store.values()
                if viewer.__class__.__name__ == cls_name]

    def _update_viewer_reference_name(
        self, old_reference, new_reference, update_id=False
    ):
        """
        Update viewer reference names.

        Viewer IDs will not be changed unless ``update_id`` is True.

        Parameters
        ----------
        old_reference : str
            The viewer reference name to be changed
        new_reference : str
            The viewer reference name to use instead of ``old_reference``
        update_id : bool, optional
            If True, update the viewer IDs as well as the viewer reference names.
        """
        if old_reference == new_reference:  # no-op
            return

        # ensure new reference is a string:
        new_reference = str(new_reference)

        viewer_reference_names = self.get_viewer_reference_names()

        if new_reference in viewer_reference_names:
            raise ValueError(f"Viewer with reference='{new_reference}' already exists.")

        if old_reference == 'imviz-0':
            raise ValueError(f"The default Imviz viewer reference "
                             f"'{old_reference}' cannot be changed.")

        if old_reference not in viewer_reference_names:
            raise ValueError(f"Viewer with reference='{old_reference}' does not exist.")

        # update the viewer item's reference name
        viewer_item = self._get_viewer_item(old_reference)
        viewer_item['reference'] = new_reference

        if viewer_item['name'] == old_reference:
            viewer_item['name'] = new_reference

        # optionally update the viewer IDs:
        if update_id:
            old_id = viewer_item['id']
            viewer_item['id'] = new_reference
            self._viewer_store[new_reference] = self._viewer_store.pop(old_id)
            self._viewer_store[new_reference]._reference_id = new_reference
            self.state.viewer_icons[new_reference] = self.state.viewer_icons.pop(old_id)

        # update the viewer name attributes on the helper:
        old_viewer_ref_attrs = [
            attr for attr in dir(self._jdaviz_helper)
            if attr.startswith('_default_') and
            getattr(self._jdaviz_helper, attr) == old_reference
        ]
        if old_viewer_ref_attrs:
            # if there is an attr to update, update it:
            setattr(self._jdaviz_helper, old_viewer_ref_attrs[0], new_reference)

        self.hub.broadcast(ViewerRenamedMessage(old_reference, new_reference, sender=self))

    def _get_first_viewer_reference_name(
            self, require_no_selected_data=False,
            require_spectrum_viewer=False,
            require_spectrum_2d_viewer=False,
            require_table_viewer=False,
            require_flux_viewer=False,
            require_image_viewer=False,
            require_profile_viewer=False,
    ):
        """
        Return the viewer reference name of the first available viewer.
        Optionally use ``require_no_selected_data`` to require that the
        viewer has not yet loaded data, or e.g. ``require_spectrum_viewer``
        to require that the viewer supports spectrum visualization.
        """
        from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
        from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer, Spectrum2DViewer
        from jdaviz.configs.cubeviz.plugins.viewers import CubevizProfileView, CubevizImageView
        from jdaviz.configs.mosviz.plugins.viewers import (
            MosvizTableViewer, MosvizProfile2DView
        )
        from jdaviz.configs.rampviz.plugins.viewers import (
            RampvizImageView, RampvizProfileView
        )

        spectral_viewers = (Spectrum1DViewer, CubevizProfileView)
        spectral_2d_viewers = (Spectrum2DViewer, MosvizProfile2DView)
        table_viewers = (MosvizTableViewer, )
        image_viewers = (ImvizImageView, CubevizImageView, RampvizImageView)
        flux_viewers = (CubevizImageView, RampvizImageView)
        ramp_viewers = (RampvizProfileView, )

        for vid in self._viewer_store:
            viewer_item = self._viewer_item_by_id(vid)
            is_returnable = (
                (require_no_selected_data and not len(viewer_item['selected_data_items'])) or
                (not require_no_selected_data)
            )
            if require_spectrum_viewer:
                if isinstance(self._viewer_store[vid], spectral_viewers) and is_returnable:
                    return viewer_item['reference']
            elif require_spectrum_2d_viewer:
                if isinstance(self._viewer_store[vid], spectral_2d_viewers) and is_returnable:
                    return viewer_item['reference']
            elif require_table_viewer:
                if isinstance(self._viewer_store[vid], table_viewers) and is_returnable:
                    return viewer_item['reference']
            elif require_image_viewer:
                if isinstance(self._viewer_store[vid], image_viewers) and is_returnable:
                    return viewer_item['reference']
            elif require_flux_viewer:
                if isinstance(self._viewer_store[vid], flux_viewers) and is_returnable:
                    return viewer_item['reference']
            elif require_profile_viewer:
                if isinstance(self._viewer_store[vid], ramp_viewers) and is_returnable:
                    return viewer_item['reference']
            else:
                if is_returnable:
                    return viewer_item['reference']

    def _viewer_by_id(self, vid):
        """
        Viewer instance by id.

        Parameters
        ----------
        vid : str
            The UUID associated with the parent viewer item dictionary.

        Returns
        -------
        `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        return self._viewer_store.get(vid)

    def _viewer_item_by_id(self, vid):
        """
        Retrieve a viewer item dictionary by id.

        Parameters
        ----------
        vid : str
            The UUID associated with the desired viewer item.

        Returns
        -------
        viewer_item : dict
            The dictionary containing the viewer instances and associated
            attributes.
        """
        def find_viewer_item(stack_items):
            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item.get('id') == vid:
                        return viewer_item

                if len(stack_item.get('children')) > 0:
                    result = find_viewer_item(stack_item.get('children'))
                    if result is not None:
                        return result

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    def _viewer_by_reference(self, reference, fallback_to_id=False):
        """
        Viewer instance by reference defined in the yaml configuration file.

        Parameters
        ----------
        reference : str
            Reference for viewer defined in the yaml configuration file.

        Returns
        -------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The viewer class instance.
        """
        viewer_item = self._viewer_item_by_reference(reference)

        if viewer_item is None and fallback_to_id:
            return self._viewer_by_id(reference)

        return self._viewer_store[viewer_item['id']]

    def _viewer_item_by_reference(self, reference):
        """
        Retrieve a viewer item dictionary by reference.

        Parameters
        ----------
        reference : str
            Reference for viewer defined in the yaml configuration file.

        Returns
        -------
        viewer_item : dict
            The dictionary containing the viewer instances and associated
            attributes.
        """
        def find_viewer_item(stack_items):
            out_viewer_item = None

            for stack_item in stack_items:
                for viewer_item in stack_item.get('viewers'):
                    if viewer_item['reference'] == reference:
                        out_viewer_item = viewer_item
                        break

                if len(stack_item.get('children')) > 0:
                    out_viewer_item = find_viewer_item(stack_item.get('children'))

            return out_viewer_item

        viewer_item = find_viewer_item(self.state.stack_items)

        return viewer_item

    def _get_viewer_item(self, ref_or_id):
        """
        Retrieve a viewer item dictionary by reference or id (trying reference first).

        Parameters
        ----------
        ref_or_id : str
            Reference or ID for viewer defined in the yaml configuration file.

        Returns
        -------
        viewer_item : dict
            The dictionary containing the viewer instances and associated
            attributes.
        """
        if isinstance(ref_or_id, dict):
            return ref_or_id

        viewer_item = self._viewer_item_by_reference(ref_or_id)
        if viewer_item is None:  # Maybe they mean the ID
            viewer_item = self._viewer_item_by_id(ref_or_id)
        return viewer_item

    def _check_valid_subset_label(self, subset_name, raise_if_invalid=True):
        """Check that `subset_name` is a valid choice for a subset name. This
        check is run when renaming subsets.

        A valid subset name must not be the name of another subset in the data
        collection (case insensitive? there cant be a subset 1 and a Subset 1.)
        The name may match a subset in the data collection if it the current
        active selection (i.e the renaming is not really a renaming, it is
        just keeping the old name, which is valid).

        Unlike dataset names, the attempted renaming of a subset to an existing
        subset label will not append a number (e.g Subset 1 repeated because
        Subset 1(1)). If the name exists, a warning will be raised and the
        original subset name will be returned.

        """

        # get active selection, if there is one
        if self.session.edit_subset_mode.edit_subset == []:
            subset_selected = None
        else:
            subset_selected = self.session.edit_subset_mode.edit_subset[0].label

        # remove the current selection label from the set of labels, because its ok
        # if the new subset shares the name of the current selection (renaming to current name)
        if subset_selected in self._reserved_labels:
            self._reserved_labels.remove(subset_selected)

        # now check `subset_name` against list of non-active current subset labels
        # and warn and return if it is
        if subset_name in self._reserved_labels:
            if raise_if_invalid:
                raise ValueError("Cannot rename subset to name of an existing subset"
                                 f" or data item: ({subset_name}).")
            return False

        elif not subset_name.replace(" ", "").isalnum():
            if raise_if_invalid:
                raise ValueError("Subset labels must be purely alphanumeric")
            return False

        else:
            split_label = subset_name.split(" ")
            if len(split_label) > 1:
                if split_label[0] == "Subset" and split_label[1].isdigit():
                    if raise_if_invalid:
                        raise ValueError("The pattern 'Subset N' is reserved for "
                                         "auto-generated labels")
                    return False

        return True

    def _rename_subset(self, old_label, new_label, subset_group=None, check_valid=True):
        # Change the label of a subset, making sure it propagates to as many places as it can
        # I don't think there's an easier way to get subset_group by label, it's just a tuple
        if subset_group is None:
            for s in self.data_collection.subset_groups:
                if s.label == old_label:
                    subset_group = s
                    break
            # If we couldn't find a matching subset group, raise an error
            else:
                raise ValueError(f"No subset named {old_label} to rename")

        if check_valid:
            if self._check_valid_subset_label(new_label):
                subset_group.label = new_label
        else:
            subset_group.label = new_label

        # Update layer icon
        self.state.layer_icons[new_label] = self.state.layer_icons[old_label]
        _ = self.state.layer_icons.pop(old_label)

        # Updated derived data if applicable
        for d in self.data_collection:
            data_renamed = False
            # Extracted spectra are named, e.g., 'Data (Subset 1, sum)'
            if d.label.split("(")[-1].split(",")[0] == old_label:
                old_data_label = d.label
                new_data_label = d.label.replace(old_label, new_label)
                d.label = new_data_label
                self.state.layer_icons[new_data_label] = self.state.layer_icons[old_data_label]
                _ = self.state.layer_icons.pop(old_data_label)

                # Update the entries in the old data menu
                for data_item in self.state.data_items:
                    if data_item['name'] == old_data_label:
                        data_item['name'] = new_data_label

            # Update live plugin results subscriptions
            if hasattr(d, 'meta') and '_update_live_plugin_results' in d.meta:
                results_dict = d.meta['_update_live_plugin_results']
                for key in results_dict.get('_subscriptions', {}).get('subset'):
                    if results_dict[key] == old_label:
                        results_dict[key] = new_label

                if data_renamed:
                    results_dict['add_results']['label'] = new_data_label

                d.meta['_update_live_plugin_results'] = results_dict

        self.hub.broadcast(SubsetRenameMessage(subset_group, old_label, new_label, sender=self))

    def _reparent_subsets(self, old_parent, new_parent=None):
        '''
        Re-parent subsets that belong to the specified data

        Parameters
        ----------
        old_parent : glue.core.Data, str
            The item from the data collection off of which to move the subset definitions.

        new_parent : glue.core.Data, str
            The item from the data collection to make the new parent. If None, the first
            item in the data collection that doesn't match ``old_parent`` will be chosen.
        '''
        from astropy.wcs.utils import pixel_to_pixel
        from jdaviz.configs.imviz.wcs_utils import get_compass_info

        if isinstance(old_parent, str):
            old_parent = self.data_collection[old_parent]

        if isinstance(new_parent, str):
            new_parent = self.data_collection[new_parent]
        elif new_parent is None:
            for data in self.data_collection:
                if data is not old_parent:
                    new_parent = data
                    break

        # Set subset attributes to match a remaining data collection member, using get_subsets to
        # get components of composite subsets.
        for key, subset_list in self.get_subsets(simplify_spectral=False).items():
            # Get the subset group entry for later. Unfortunately can't just index on label.
            [subset_group] = [sg for sg in self.data_collection.subset_groups if sg.label == key]

            for subset in subset_list:
                subset_state = subset['subset_state']
                # Only reparent if needed
                if subset_state.attributes[0].parent is old_parent:
                    for att in ("att", "xatt", "yatt", "x_att", "y_att"):
                        if hasattr(subset_state, att):
                            subset_att = getattr(subset_state, att)
                            data_components = new_parent.components
                            if subset_att not in data_components:
                                cid = [c for c in data_components if c.label == subset_att.label][0]
                                setattr(subset_state, att, cid)

                    # Translate bounds through WCS if needed
                    if (self.config == "imviz" and
                            self._jdaviz_helper.plugins["Orientation"].align_by == "WCS"):

                        # Default shape for WCS-only layers is 10x10, but it doesn't really matter
                        # since we only need the angles.
                        old_angle, _, old_flip = get_compass_info(old_parent.coords, (10, 10))[-3:]
                        new_angle, _, new_flip = get_compass_info(new_parent.coords, (10, 10))[-3:]
                        if old_flip != new_flip:
                            # Note that this won't work for an irregular/assymetric region if we
                            # ever implement those.
                            relative_angle = 180 - new_angle - old_angle
                        else:
                            relative_angle = new_angle - old_angle

                        # Get the correct link to use for translation
                        roi = subset_state.roi
                        old_xc, old_yc = subset_state.center()
                        if isinstance(roi, (CircularROI, CircularAnnulusROI, EllipticalROI)):
                            # Convert center
                            x, y = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                  roi.xc, roi.yc)
                            subset_state.move_to(x, y)

                            for att in ("radius", "inner_radius", "outer_radius",
                                        "radius_x", "radius_y"):
                                # Hacky way to get new radii with point on edge of circle
                                # Do we need to worry about using x for the radius conversion for
                                # radius_y if there is distortion?
                                r = getattr(roi, att, None)
                                if r is not None:
                                    dummy_x = old_xc + r
                                    x2, y2 = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                            dummy_x, old_yc)
                                    # Need to use x and y in this radius calculation because the
                                    # new orientation is likely rotated compared to the original.
                                    new_radius = np.sqrt((x2 - x)**2 + (y2 - y)**2)
                                    setattr(roi, att, new_radius)

                        elif isinstance(roi, RectangularROI):
                            x1, y1 = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                    roi.xmin, roi.ymin)
                            x2, y2 = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                    roi.xmin, roi.ymax)
                            x3, y3 = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                    roi.xmax, roi.ymin)

                            # Calculate new width and height from possibly rotated result
                            new_half_width = np.sqrt((x3-x1)**2 + (y3-y1)**2) * 0.5
                            new_half_height = np.sqrt((x2-x1)**2 + (y2-y1)**2) * 0.5

                            # Convert center
                            new_center = pixel_to_pixel(old_parent.coords, new_parent.coords,
                                                        old_xc, old_yc)

                            # New min/max before applying theta
                            roi.xmin = new_center[0] - new_half_width
                            roi.xmax = new_center[0] + new_half_width
                            roi.ymin = new_center[1] - new_half_height
                            roi.ymax = new_center[1] + new_half_height

                        # Account for rotation between orientations
                        if hasattr(roi, "theta"):
                            fac = 1.0 if (old_flip != new_flip) else -1.0
                            roi.theta = (fac * (np.deg2rad(relative_angle) - roi.theta)) % (2 * np.pi)  # noqa: E501

                    elif isinstance(subset_group.subset_state, RangeSubsetState):
                        range_state = subset_group.subset_state
                        wcs_index = (new_parent.coords.world_n_dim - 1 -
                                     new_parent.meta['spectral_axis_index'])
                        cur_unit = u.Unit(old_parent.coords.world_axis_units[wcs_index])
                        new_unit = u.Unit(new_parent.coords.world_axis_units[wcs_index])
                        if cur_unit is not new_unit:
                            range_state.lo, range_state.hi = cur_unit.to(new_unit, [range_state.lo,
                                                                                    range_state.hi])

            # Force subset plugin to update bounds and such
            for subset in subset_group.subsets:
                subset_message = SubsetUpdateMessage(sender=subset)
                self.hub.broadcast(subset_message)

    def vue_destroy_viewer_item(self, cid):
        """
        Callback for when viewer area tabs are destroyed. Finds the viewer item
        associated with the provided id and removes it from the ``stack_items``
        list.

        Parameters
        ----------
        cid : str
            The viewer ID associated with the viewer item dictionary.
        """
        def remove(stack_items):
            for stack in stack_items:
                for viewer in stack['viewers']:
                    if viewer['id'] == cid:
                        stack['viewers'].remove(viewer)

                if len(stack.get('children', [])) > 0:
                    stack['children'] = remove(stack['children'])

            for empty_stack in [s for s in stack_items
                                if not s['viewers'] and not s.get('children')]:
                stack_items.remove(empty_stack)

            return stack_items

        remove(self.state.stack_items)

        # Also remove the viewer from the stored viewer instance dictionary
        if cid in self._viewer_store:
            del self._viewer_store[cid]

        # clear from the viewer icons dictionary
        if cid in self.state.viewer_icons:
            del self.state.viewer_icons[cid]

        self.hub.broadcast(ViewerRemovedMessage(cid, sender=self))

    def vue_change_reference_data(self, event):
        self._change_reference_data(
            self._get_data_item_by_id(event['item_id'])['name'],
            viewer_id=self._get_viewer_item(event['id'])['name']
        )

    def set_data_visibility(self, viewer_reference, data_label, visible=True, replace=False):
        """
        Set the visibility of the layers corresponding to ``data_label`` in a given viewer.

        Parameters
        ----------
        viewer_reference : str
            Reference (or ID) of the viewer
        data_label : str
            Label of the data to set the visiblity.  If not already loaded in the viewer, the
            data will automatically be loaded before setting the visibility
        visible : bool
            Whether to set the layer(s) to visible.
        replace : bool
            Whether to disable the visibility of all other layers in the viewer
        """
        viewer_item = self._get_viewer_item(viewer_reference)
        viewer_id = viewer_item['id']
        viewer = self.get_viewer_by_id(viewer_id)

        # if the data_label is in the app, but not loaded in the viewer, automatically load it first
        viewer_data_labels = [layer.layer.label for layer in viewer.layers]
        if data_label not in viewer_data_labels:
            dc_labels = [data.label for data in self.data_collection]
            if data_label not in dc_labels:
                if os.path.exists(data_label):
                    raise ValueError(f'The data label "{data_label}" is not available '
                                     f'to add to the viewer, but it does specify a file path. '
                                     f'If you intended to load the data from that file, use the '
                                     f'`load_data` method or similar.')
                raise ValueError(
                    f"No data item found with label '{data_label}'. Label must be one "
                    "of:\n\t" + "\n\t".join(dc_labels))

            data = self.data_collection[data_label]

            # set the original color based on metadata preferences, if provided, and otherwise
            # based on the colorcycler
            # NOTE: this is intentionally not a single line to avoid incrementing the color-cycler
            # unless it is used
            color = data.meta.get('_default_color')
            if color is None:
                color = viewer.color_cycler()
            viewer.add_data(data, percentile=95, color=color)

            # Specviz removes the data from collection in viewer.py if flux unit incompatible.
            if data_label not in self.data_collection:
                return

            viewer.set_plot_axes()

            add_data_message = AddDataMessage(data, viewer,
                                              viewer_id=viewer_id,
                                              sender=self)
            self.hub.broadcast(add_data_message)

        assoc_children = self._get_assoc_data_children(data_label)

        # set visibility state of all applicable layers
        for layer in viewer.layers:
            layer_is_wcs_only = getattr(layer.layer, 'meta', {}).get(_wcs_only_label, False)
            if layer.layer.data.label in [data_label] + assoc_children:
                if layer_is_wcs_only:
                    layer.visible = False
                    layer.update()
                elif visible and not layer.visible:
                    layer.visible = True
                    layer.update()
                else:
                    layer.visible = visible

        # if replace, do another loop (we do a second loop to ensure the visible layer is added
        # first BEFORE other layers are removed)
        if replace:
            for layer in viewer.layers:
                if layer.layer.data.label != data_label:
                    layer.visible = False

        # if Data has children, update their visibilities to match Data:
        available_plugins = [tray_item['name'] for tray_item in self.state.tray_items]
        for child in assoc_children:
            if child not in viewer.data_menu.data_labels_loaded:
                self.add_data_to_viewer(viewer.reference, child, visible=visible)

            if 'g-data-quality' in available_plugins and visible:
                # if we're adding a DQ layer to a viewer, make sure that
                # the layer is appropriately colormapped as DQ:
                data_quality_plugin = self.get_tray_item_from_name('g-data-quality')
                old_viewer = data_quality_plugin.viewer_selected
                data_quality_plugin.viewer_selected = viewer.reference
                data_quality_plugin.science_layer_selected = data_label
                data_quality_plugin.dq_layer_selected = child
                data_quality_plugin.init_decoding(viewers=[viewer])
                data_quality_plugin.viewer_selected = old_viewer

        for layer in viewer.layers:
            if layer.layer.data.label in assoc_children:
                if visible and not layer.visible:
                    layer.visible = True
                    layer.update()
                else:
                    layer.visible = visible

        # Sets the plot axes labels to be the units of the most recently
        # active data.
        viewer_data_labels = [layer.layer.label for layer in viewer.layers]
        if len(viewer_data_labels) > 0 and getattr(self._jdaviz_helper, '_in_batch_load', 0) == 0:
            # This "if" is nested on purpose to make parent "if" available
            # for other configs in the future, as needed.
            if self.config == 'imviz':
                viewer.on_limits_change()  # Trigger compass redraw

    def data_item_remove(self, data_label):
        data = self.data_collection[data_label]
        orientation_plugin = self._jdaviz_helper.plugins.get("Orientation")
        if orientation_plugin is not None and orientation_plugin.align_by == "WCS":
            from jdaviz.configs.imviz.plugins.orientation.orientation import base_wcs_layer_label
            orient = orientation_plugin.orientation.selected
            if orient == data_label:
                orient = base_wcs_layer_label
            self._reparent_subsets(data, new_parent=orient)
        else:
            self._reparent_subsets(data)

        # Make sure the data isn't loaded in any viewers and isn't the selected orientation
        for viewer_id, viewer in self._viewer_store.items():
            if orientation_plugin is not None and self._align_by == 'wcs':
                if viewer.state.reference_data.label == data_label:
                    self._change_reference_data(base_wcs_layer_label, viewer_id)
            self.remove_data_from_viewer(viewer_id, data_label)

        self.data_collection.remove(self.data_collection[data_label])

        # If there are two or more datasets left we need to link them back together if anything
        # was linked only through the removed data.
        if (len(self.data_collection) > 1 and
                len(self.data_collection.external_links) < len(self.data_collection) - 1):
            if orientation_plugin is not None:
                orientation_plugin._obj._link_image_data()
                # Hack to restore responsiveness to imviz layers
                for viewer_ref in self.get_viewer_reference_names():
                    viewer = self.get_viewer(viewer_ref)
                    loaded_layers = [layer.layer.label for layer in viewer.layers if
                                     "Subset" not in layer.layer.label and layer.layer.label
                                     not in orientation_plugin.orientation.labels]
                    if len(loaded_layers):
                        self.remove_data_from_viewer(viewer_ref, loaded_layers[-1])
                        self.add_data_to_viewer(viewer_ref, loaded_layers[-1])
            else:
                for i in range(1, len(self.data_collection)):
                    self._link_new_data(data_to_be_linked=i)

    def vue_close_snackbar_message(self, event):
        """
        Callback to close a message in the snackbar when the "close"
        button is clicked.
        """
        self.state.snackbar_queue.close_current_message(self.state)

    def vue_call_viewer_method(self, event):
        viewer_id, method = event['id'], event['method']
        args = event.get('args', [])
        kwargs = event.get('kwargs', {})
        return getattr(self._viewer_store[viewer_id], method)(*args, **kwargs)

    def vue_search_item_clicked(self, event):
        attr, label = event['attr'], event['label']
        if attr == 'data_menus':
            item = self._jdaviz_helper.viewers[label].data_menu
        else:
            item = getattr(self._jdaviz_helper, attr)[label]
        if label == 'About':
            item.show_popup()
        elif attr == 'data_menus':
            item.open_menu()
        else:
            kw = {'scroll_to': item._obj._sidebar == 'plugins'} if attr == 'plugins' else {}  # noqa
            item.open_in_tray(**kw)

    def _get_data_item_by_id(self, data_id):
        return next((x for x in self.state.data_items
                     if x['id'] == data_id), None)

    def _on_data_added(self, msg):
        """
        Callback for when data is added to the internal ``DataCollection``.
        Adds a new data item dictionary to the ``data_items`` state list and
        links the new data to any compatible previously loaded data.

        Parameters
        ----------
        msg : `~glue.core.message.DataCollectionAddMessage`
            The Glue data collection add message containing information about
            the new data.
        """
        # We don't need to link the first data to itself
        if len(self.data_collection) > 1:
            self._link_new_data()
        data_item = self._create_data_item(msg.data)
        self.state.data_items.append(data_item)
        self._reserved_labels.add(msg.data.label)

    def _clear_object_cache(self, data_label=None):
        if data_label is None:
            self._get_object_cache.clear()
        else:
            # keys are (data_label, statistic) tuples
            self._get_object_cache = {k: v for k, v in self._get_object_cache.items()
                                      if k[0] != data_label}

    def _on_data_deleted(self, msg):
        """
        Callback for when data is removed from the internal ``DataCollection``.
        Removes the data item dictionary in the ``data_items`` state list.

        Parameters
        ----------
        msg : `~glue.core.message.DataCollectionAddMessage`
            The Glue data collection add message containing information about
            the new data.
        """
        for data_item in self.state.data_items:
            if data_item['name'] == msg.data.label:
                self.state.data_items.remove(data_item)

        self._clear_object_cache(msg.data.label)

    def _create_data_item(self, data):
        ndims = len(data.shape)
        wcsaxes = data.meta.get('WCSAXES', None)
        wcs_only = data.meta.get(_wcs_only_label, False)
        if wcsaxes is None:
            # then we'll need to determine type another way, we want to avoid
            # this when we can though since its not as cheap
            component_ids = [str(c) for c in data.component_ids()]

        if wcs_only:
            typ = 'wcs-only'
        elif data.label == 'MOS Table':
            typ = 'table'
        elif 'Trace' in data.meta:
            typ = 'trace'
        elif ndims == 1:
            typ = '1d spectrum'
        elif ndims == 2 and wcsaxes is not None:
            if wcsaxes == 3:
                typ = '2d spectrum'
            elif wcsaxes == 2:
                typ = 'image'
            else:
                typ = 'unknown'
        elif ndims == 2 and wcsaxes is None:
            typ = '2d spectrum' if 'Wavelength' in component_ids else 'image'
        elif ndims == 3:
            typ = 'cube'
        else:
            typ = 'unknown'

        # we'll expose any information we need here.  For "meta", not all entries are guaranteed
        # to be serializable, so we'll just send those that we need.

        def _expose_meta(key):
            """
            Whether to expose this metadata entry from the glue data object to the vue-frontend
            via the data-item, based on the dictionary key.
            """
            if key in ('Plugin', 'mosviz_row'):
                # mosviz_row is used to hide entries from the spectrum1d/2d viewers if they
                # do not correspond to the currently selected row
                return True
            if key.lower().startswith(f'_{self.config}'):
                # other internal metadata (like lcviz's '_LCVIZ_EPHEMERIS')
                # _LCVIZ_EPHEMERIS is used in lcviz to only display data phased to a specific
                # ephemeris in the appropriate viewer
                return True
            return False

        return {
            'id': str(uuid.uuid4()),
            'name': data.label,
            'locked': False,
            'ndims': data.ndim,
            'type': typ,
            'has_wcs': data_has_valid_wcs(data),
            'is_astrowidgets_markers_table': (self.config == "imviz") and layer_is_table_data(data),
            'meta': {k: v for k, v in data.meta.items() if _expose_meta(k)},
            'children': [],
            'parent': None,
        }

    @staticmethod
    def _create_stack_item(container='gl-stack', children=None, viewers=None):
        """
        Convenience method for generating stack item dictionaries.

        Parameters
        ----------
        container : str
            The GoldenLayout container type used to encapsulate the children
            items within this stack item.
        children : list
            List of children stack item dictionaries used for recursively
            including layout items within each GoldenLayout component cell.
        viewers : list
            List of viewer item dictionaries containing the information used
            to render the viewer and associated tool widgets.

        Returns
        -------
        dict
            Dictionary containing information for this stack item.
        """
        children = [] if children is None else children
        viewers = [] if viewers is None else viewers

        return {
            'id': str(uuid.uuid4()),
            'container': container,
            'children': children,
            'viewers': viewers}

    def _next_viewer_num(self, prefix):
        all_vids = self.get_viewer_ids(prefix=prefix)
        if len(all_vids) == 0:
            return 0

        # Assume name-num format
        last_vid = all_vids[-1]
        last_num = int(last_vid.split('-')[-1])
        return last_num + 1

    def _create_viewer_item(self, viewer, vid=None, name=None, reference=None,
                            open_data_menu_if_empty=True):
        """
        Convenience method for generating viewer item dictionaries.

        Parameters
        ----------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The ``Bqplot`` viewer instance.
        vid : str or `None`, optional
            The ID of the viewer.
        name : str or `None`, optional
            The name shown in the GoldenLayout tab for this viewer.
            If `None`, it is the same as viewer ID.
        reference : str, optional
            The reference associated with this viewer as defined in the yaml
            configuration file.
        open_data_menu_if_empty : bool, optional
            Whether the data menu should be opened when creating the viewer if the viewer is
            empty.  Pass this as False if immediately populating the viewer.
        Returns
        -------
        dict
            Dictionary containing information for this viewer item.
        """
        if vid is None:
            pfx = self.state.settings.get('configuration', str(name))
            n = self._next_viewer_num(pfx)
            vid = f"{pfx}-{n}"

        # There is a viewer.LABEL inherited from glue-jupyter but there was
        # objection in using it here because it is not hidden, so we use our
        # own attribute instead.
        viewer._reference_id = vid  # For reverse look-up

        if vid not in self.state.viewer_icons:
            self.state.viewer_icons = {**self.state.viewer_icons,
                                       vid: len(self.state.viewer_icons) + 1}
            # for some reason that state callback is not triggering this
            self.hub.broadcast(IconsUpdatedMessage('viewer',
                                                   self.state.viewer_icons,
                                                   sender=self)
                               )

        reference_data = getattr(viewer.state, 'reference_data', None)
        reference_data_label = getattr(reference_data, 'label', None)
        linked_by_wcs = getattr(viewer.state, 'linked_by_wcs', False)

        return {
            'id': vid,
            'name': name or vid,
            'widget': "IPY_MODEL_" + viewer.figure_widget.model_id,
            'toolbar': "IPY_MODEL_" + viewer.toolbar.model_id if viewer.toolbar else '',  # noqa
            'data_menu': 'IPY_MODEL_' + viewer._data_menu.model_id if hasattr(viewer, '_data_menu') else '',  # noqa
            'api_methods': viewer._data_menu.api_methods if hasattr(viewer, '_data_menu') else [],
            'reference_data_label': reference_data_label,
            'canvas_angle': 0,  # canvas rotation clockwise rotation angle in deg
            'canvas_flip_horizontal': False,  # canvas rotation horizontal flip
            'config': self.config,  # give viewer access to app config/layout
            'collapse': True,
            'reference': reference or name or vid,
            'linked_by_wcs': linked_by_wcs,
        }

    def _on_new_viewer(self, msg, vid=None, name=None, add_layers_to_viewer=False,
                       open_data_menu_if_empty=True):
        """
        Callback for when the `~jdaviz.core.events.NewViewerMessage` message is
        raised. This method asks the application handler to generate a new
        viewer and then created the associated stack and viewer items.

        Parameters
        ----------
        msg : `~jdaviz.core.events.NewViewerMessage`
            The message received from the ``Hub`` broadcast.

        vid : str or `None`
            ID of the viewer. If `None`, it is auto-generated
            from configuration settings.

        name : str or `None`
            Name of the viewer. If `None`, it is auto-generated
            from class name.

        open_data_menu_if_empty : bool, optional
            Whether the data menu should be opened when creating the viewer if the viewer is
            empty.  Pass this as False if immediately populating the viewer.

        Returns
        -------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The new viewer instance.
        """

        viewer = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)
        viewer.figure_widget.layout.height = '100%'

        linked_by_wcs = self._align_by == 'wcs'

        if hasattr(viewer.state, 'linked_by_wcs'):
            orientation_plugin = self._jdaviz_helper.plugins.get('Orientation', None)
            if orientation_plugin is not None:
                linked_by_wcs = orientation_plugin.align_by.selected == 'WCS'
            elif len(self._viewer_store) and hasattr(self._jdaviz_helper, 'default_viewer'):
                # The plugin would only not exist for instances of Imviz where the user has
                # intentionally removed the Orientation plugin, but in that case we will
                # adopt "linked_by_wcs" from the first (assuming all are the same)
                # NOTE: deleting the default viewer is forbidden both by API and UI, but if
                # for some reason that was the case here, linked_by_wcs will default to False
                linked_by_wcs = self._jdaviz_helper.default_viewer._obj.state.linked_by_wcs
            else:
                linked_by_wcs = False
            viewer.state.linked_by_wcs = linked_by_wcs

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            viewer.state.x_att = x

        # Create the viewer item dictionary
        if name is None:
            name = vid
        new_viewer_item = self._create_viewer_item(
            viewer=viewer, vid=vid, name=name, reference=name,
            open_data_menu_if_empty=open_data_menu_if_empty
        )

        if self.config == 'imviz':
            # NOTE: if ever extending image rotation beyond imviz or adding non-image viewers
            # to imviz: this currently assumes that the helper has a default_viewer and that is an
            # image viewer
            ref_data = self._jdaviz_helper.default_viewer._obj.state.reference_data
            new_viewer_item['reference_data_label'] = getattr(ref_data, 'label', None)

            if hasattr(viewer, 'reference'):
                viewer.state.reference_data = ref_data

        new_stack_item = self._create_stack_item(
            container='gl-stack',
            viewers=[new_viewer_item])

        self.state.viewer_items.append(new_viewer_item)

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        vid = new_viewer_item['id']
        self._viewer_store[vid] = viewer

        # Add viewer locally
        if (self.config in ('deconfigged', 'specviz', 'specviz2d', 'lcviz')
                and len(self.state.stack_items)):
            # add to bottom (eventually will want more control in placement)
            self.state.stack_items[0]['children'].append(new_stack_item)
        else:
            self.state.stack_items.append(new_stack_item)

        self.session.application.viewers.append(viewer)

        if add_layers_to_viewer:
            for layer_label in add_layers_to_viewer:
                if hasattr(viewer, 'reference'):
                    self.add_data_to_viewer(viewer.reference, layer_label)

        # Send out a toast message
        self.hub.broadcast(ViewerAddedMessage(vid, sender=self))

        return viewer

    def load_configuration(self, path=None, config=None):
        """
        Parses the provided input into a configuration
        dictionary and populates the appropriate state values
        with the results.  Provided input can either be a
        configuration YAML file or a pre-made configuration
        dictionary.

        Parameters
        ----------
        path : str, optional
            Path to the configuration file to be loaded. In the case where this
            is ``None``, it loads the default configuration. Optionally, this
            can be provided as name reference. **NOTE** This optional way to
            define the configuration will be removed in future versions.
        config : dict, optional
            A dictionary of configuration settings to be loaded.  The dictionary
            contents should be the same as a YAML config file specification.
        """
        # reset the application state
        self._reset_state()

        # load the configuration from the yaml file or configuration object
        assert not (path and config), 'Cannot specify both a path and a config object!'
        if config:
            assert isinstance(config, dict), 'configuration object must be a dictionary'
        else:
            # check if the input path is actually a dict object
            if isinstance(path, dict):
                config = path
            else:
                config = read_configuration(path=path)

        # store the loaded config object
        self._loaded_configuration = config
        # give the vue templates access to the current config/layout
        self.config = config['settings'].get('configuration', 'unknown').lower()
        self.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__
        if self.config in ALL_JDAVIZ_CONFIGS:
            self.docs_link = f'https://jdaviz.readthedocs.io/en/{self.vdocs}/{self.config}/index.html'  # noqa
        else:
            self.docs_link = f'https://jdaviz.readthedocs.io/en/{self.vdocs}'

        self.state.settings.update(config.get('settings'))

        def compose_viewer_area(viewer_area_items):
            stack_items = []

            for item in viewer_area_items:
                stack_item = self._create_stack_item(
                    container=CONTAINER_TYPES[item.get('container')])

                stack_items.append(stack_item)

                for view in item.get('viewers', []):
                    viewer = self._application_handler.new_data_viewer(
                        viewer_registry.members.get(view['plot'])['cls'],
                        data=None, show=False)
                    viewer.figure_widget.layout.height = '100%'

                    viewer_item = self._create_viewer_item(
                        name=view.get('name'),
                        viewer=viewer,
                        reference=view.get('reference'))

                    self._viewer_store[viewer_item['id']] = viewer

                    stack_item.get('viewers').append(viewer_item)

                if len(item.get('children', [])) > 0:
                    child_stack_items = compose_viewer_area(
                        item.get('children'))
                    stack_item['children'] = child_stack_items

            return stack_items

        if config.get('viewer_area') is not None:
            stack_items = compose_viewer_area(config.get('viewer_area'))
            self.state.stack_items.extend(stack_items)

        # Add the toolbar item filter to the toolbar component
        for name in config.get('toolbar', []):
            tool = tool_registry.members.get(name)(app=self)

            self.state.tool_items.append({
                'name': name,
                'widget': "IPY_MODEL_" + tool.model_id
            })

            self._application_handler._tools[name] = tool

        # Loaders
        def open():
            self.state.drawer_content = 'loaders'  # TODO: rename to "add"?
            self.state.add_subtab = 0

        def close():
            self.state.loader_selected = ''

        def set_active_loader(resolver):
            self.state.loader_selected = resolver

        # registry will be populated at import
        import jdaviz.core.loaders  # noqa
        for name, Resolver in loader_resolver_registry.members.items():
            loader = Resolver(app=self,
                              open_callback=open,
                              close_callback=close,
                              set_active_loader_callback=set_active_loader)
            self.state.loader_items.append({
                'name': name,
                'label': name,
                'requires_api_support': loader.requires_api_support,
                'widget': "IPY_MODEL_" + loader.model_id,
                'api_methods': loader.api_methods,
            })
        # initialize selection (tab) to first entry
        if len(self.state.loader_items):
            self.state.loader_selected = self.state.loader_items[0]['name']

        # Tray plugins
        if self.config == 'deconfigged':
            self.update_tray_items_from_registry()
            import jdaviz.core.viewer_creators  # noqa
            self.update_new_viewers_from_registry()
        else:
            for name in config.get('tray', []):
                tray_registry_member = tray_registry.members.get(name)
                self.state.tray_items.append(self._create_tray_item(tray_registry_member))

    def update_loaders_from_registry(self):
        if self.config != 'deconfigged':
            raise NotImplementedError("update_loaders_from_registry is only "
                                      "implemented for the deconfigged app")
        for loader in self._jdaviz_helper.loaders.values():
            loader.format._update_items()

    def update_tray_items_from_registry(self):
        if self.config != 'deconfigged':
            raise NotImplementedError("update_tray_items_from_registry is only "
                                      "implemented for the deconfigged app")
        # need to rebuild in order, just pulling from existing dict if its already there
        tray_items = []
        for category in ['app:options', 'data:reduction',
                         'data:manipulation', 'data:analysis',
                         'core']:
            for tray_registry_member in tray_registry.members_in_category(category):
                if not tray_registry_member.get('overwrite', False):
                    try:
                        tray_item = self.get_tray_item_from_name(
                            tray_registry_member.get('name'), return_widget=False)
                    except KeyError:
                        create_new = True
                    else:
                        create_new = False
                else:
                    create_new = True

                if create_new:
                    try:
                        tray_item = self._create_tray_item(tray_registry_member)
                    except Exception as e:
                        self.hub.broadcast(SnackbarMessage(
                            f"Failed to load plugin {tray_registry_member.get('name')}: {e}",
                            sender=self, color='error'))
                tray_items.append(tray_item)

        self.state.tray_items = tray_items

    def _create_tray_item(self, tray_registry_member):
        tray_item_instance = tray_registry_member.get('cls')(app=self, tray_instance=True)

        # store a copy of the tray name in the instance so it can be accessed by the
        # plugin itself
        tray_item_label = tray_registry_member.get('label')

        tray_item_description = tray_item_instance.plugin_description
        # NOTE: is_relevant is later updated by observing irrelvant_msg traitlet
        tray_item = {
            'name': tray_registry_member.get('name'),
            'label': tray_item_label,
            'sidebar': tray_item_instance._sidebar,
            'subtab': tray_item_instance._subtab,
            'tray_item_description': tray_item_description,
            'api_methods': tray_item_instance.api_methods,
            'is_relevant': len(tray_item_instance.irrelevant_msg) == 0,
            'widget': "IPY_MODEL_" + tray_item_instance.model_id
        }
        return tray_item

    def update_new_viewers_from_registry(self):
        # TODO: implement jdaviz.new_viewers dictionary to instantiated items here
        if self.config != 'deconfigged':
            raise NotImplementedError("update_new_viewers_from_registry is only "
                                      "implemented for the deconfigged app")

        # need to rebuild in order, just pulling from existing dict if its already there
        new_viewer_items = []
        for name, vc_registry_member in viewer_creator_registry.members.items():
            try:
                item = self.get_new_viewer_item_from_name(
                            name, return_widget=False)
            except KeyError:
                try:
                    item = self._create_new_viewer_item(vc_registry_member)
                except Exception as e:
                    self.hub.broadcast(SnackbarMessage(
                        f"Failed to load viewer {name}: {e}",
                        sender=self, color='error'))
                    continue

            new_viewer_items.append(item)

        self.state.new_viewer_items = new_viewer_items
        relevant_items = [nvi for nvi in new_viewer_items if nvi['is_relevant']]
        if not len(self.state.new_viewer_selected) and len(relevant_items):
            self.state.new_viewer_selected = relevant_items[0]['label']

    def _create_new_viewer_item(self, vc_registry_member):
        def open():
            self.state.drawer_content = 'loaders'  # TODO: rename to "add"?
            self.state.add_subtab = 1

        def close():
            self.state.new_viewer_selected = ''

        def set_active_viewer_creator(new_viewer_label):
            self.state.new_viewer_selected = new_viewer_label

        vc_instance = vc_registry_member(app=self,
                                         open_callback=open,
                                         close_callback=close,
                                         set_active_callback=set_active_viewer_creator)
        new_viewer_item = {
            'label': vc_registry_member._registry_label,
            'widget': "IPY_MODEL_" + vc_instance.model_id,
            'api_methods': vc_instance.api_methods,
            'is_relevant': vc_instance.is_relevant,
        }
        return new_viewer_item

    def get_new_viewer_item_from_name(self, name, return_widget=True):
        return self._get_state_item_from_name(self.state.new_viewer_items,
                                              name, return_widget)

    def _reset_state(self):
        """ Resets the application state """
        self.state = ApplicationState()
        self._application_handler._tools = {}

    def get_configuration(self, path=None, section=None):
        """Returns a copy of the application configuration.

        Returns a copy of the configuration specification. If path
        is not specified, returns the currently loaded configuration.

        Parameters
        ----------
        path : str, optional
            path to the configuration file to be retrieved.
        section : str, optional
            A section of the configuration to retrieve.

        Returns
        -------
        cfg : dict
            A configuration specification dictionary.

        """

        config = None
        if not path:
            config = self._loaded_configuration

        cfg = get_configuration(path=path, section=section, config=config)
        return cfg

    def _get_state_item_from_name(self, state_list, name, return_widget=True):
        from ipywidgets.widgets import widget_serialization

        ret_item = None
        for item in state_list:
            if item.get('name') == name or item.get('label') == name:
                ipy_model_id = item['widget']
                if return_widget:
                    ret_item = widget_serialization['from_json'](ipy_model_id, None)
                else:
                    ret_item = item
                break

        if ret_item is None:
            raise KeyError(f'{name} not found')

        return ret_item

    def get_tray_item_from_name(self, name, return_widget=True):
        """Return the instance of a tray item for a given name.
        This is useful for direct programmatic access to Jdaviz plugins
        registered under tray items.

        Parameters
        ----------
        name : str
            The name used when the plugin was registered to
            an internal `~jdaviz.core.registries.TrayRegistry`.

        Returns
        -------
        tray_item : obj
            The instance of the plugin registered to tray items.

        Raises
        ------
        KeyError
            Name not found.
        """
        return self._get_state_item_from_name(self.state.tray_items, name, return_widget)

    def _init_data_associations(self):
        # assume all Data are parents:
        data_associations = {
            data.label: {'parent': None, 'children': []}
            for data in self.data_collection
        }
        return data_associations

    def _add_assoc_data_as_parent(self, data_label):
        self._data_associations[data_label] = {'parent': None, 'children': []}

    def _set_assoc_data_as_child(self, data_label, new_parent_label):
        for data_item in self.state.data_items:
            if data_item['name'] == data_label:
                child_id = data_item['id']
            elif data_item['name'] == new_parent_label:
                new_parent_id = data_item['id']

        # Data has a new parent:
        self._data_associations[data_label]['parent'] = new_parent_label

        # parent has a new child:
        self._data_associations[new_parent_label]['children'].append(data_label)

        # update the data item so vue can see the change:
        for data_item in self.state.data_items:
            if data_item['name'] == data_label:
                data_item['parent'] = new_parent_id
            elif data_item['name'] == new_parent_label:
                data_item['children'].append(child_id)

    def _get_assoc_data_children(self, data_label):
        # intentionally not recursive for now, just one generation:
        return self._data_associations.get(data_label, {}).get('children', [])

    def _get_assoc_data_parent(self, data_label):
        return self._data_associations.get(data_label, {}).get('parent')
