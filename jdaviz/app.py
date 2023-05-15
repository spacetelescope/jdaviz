import os
import pathlib
import re
import uuid
import warnings
from inspect import isclass
import operator

from ipywidgets import widget_serialization
import ipyvue

from astropy import units as u
from astropy.nddata import CCDData, NDData
from astropy.io import fits
from astropy.time import Time
from astropy.utils.decorators import deprecated
from echo import CallbackProperty, DictCallbackProperty, ListCallbackProperty
from ipygoldenlayout import GoldenLayout
from ipysplitpanes import SplitPanes
from traitlets import Dict, Bool, Unicode, Any
from specutils import Spectrum1D, SpectralRegion
import matplotlib.cm as cm
import numpy as np

from glue.core.exceptions import IncompatibleAttribute
from glue.config import colormaps, data_translator
from glue.config import settings as glue_settings
from glue.core import BaseData, HubListener, Data, DataCollection
from glue.core.link_helpers import LinkSame, LinkSameWithUnits
from glue.plugins.wcs_autolinking.wcs_autolinking import WCSLink, IncompatibleWCS
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage,
                               SubsetUpdateMessage,
                               SubsetDeleteMessage)
from glue.core.state_objects import State
from glue.core.subset import (Subset, RangeSubsetState, RoiSubsetState,
                              CompositeSubsetState, InvertState)
from glue.core.units import unit_converter
from glue_astronomy.spectral_coordinates import SpectralCoordinates
from glue_astronomy.translators.regions import roi_subset_state_to_region
from glue_jupyter.app import JupyterApplication
from glue_jupyter.common.toolbar_vuetify import read_icon
from glue_jupyter.state_traitlets_helpers import GlueState
from glue_jupyter.bqplot.profile import BqplotProfileView
from ipyvuetify import VuetifyTemplate

from jdaviz import __version__
from jdaviz.core.config import read_configuration, get_configuration
from jdaviz.core.events import (LoadDataMessage, NewViewerMessage, AddDataMessage,
                                SnackbarMessage, RemoveDataMessage,
                                AddDataToViewerMessage, RemoveDataFromViewerMessage,
                                ViewerAddedMessage, ViewerRemovedMessage)
from jdaviz.core.style_widget import StyleWidget
from jdaviz.core.registries import (tool_registry, tray_registry, viewer_registry,
                                    data_parser_registry)
from jdaviz.core.tools import ICON_DIR
from jdaviz.utils import SnackbarQueue, alpha_index
from ipypopout import PopoutButton

__all__ = ['Application']

SplitPanes()
GoldenLayout()

CONTAINER_TYPES = dict(row='gl-row', col='gl-col', stack='gl-stack')
EXT_TYPES = dict(flux=['flux', 'sci'],
                 uncert=['ivar', 'err', 'var', 'uncert'],
                 mask=['mask', 'dq'])


@unit_converter('custom-jdaviz')
class UnitConverterWithSpectral:

    def equivalent_units(self, data, cid, units):
        if cid.label == "flux":
            eqv = u.spectral_density(1 * u.m)  # Value does not matter here.
            list_of_units = set(list(map(str, u.Unit(units).find_equivalent_units(
                include_prefix_units=True, equivalencies=eqv))) + [
                    'Jy', 'mJy', 'uJy',
                    'W / (m2 Hz)', 'W / (Hz m2)',  # Order is different in astropy v5.3
                    'eV / (s m2 Hz)', 'eV / (Hz s m2)',
                    'erg / (s cm2)',
                    'erg / (s cm2 Angstrom)', 'erg / (Angstrom s cm2)',
                    'erg / (s cm2 Hz)', 'erg / (Hz s cm2)',
                    'ph / (s cm2 Angstrom)', 'ph / (Angstrom s cm2)',
                    'ph / (s cm2 Hz)', 'ph / (Hz s cm2)'
                ])
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
        if cid.label == "flux":
            spec = data.get_object(cls=Spectrum1D)
            if len(values) == 2:
                # Need this for setting the y-limits
                spec_limits = [spec.spectral_axis[0].value, spec.spectral_axis[-1].value]
                eqv = u.spectral_density(spec_limits*spec.spectral_axis.unit)
            else:
                eqv = u.spectral_density(spec.spectral_axis)
        else:  # spectral axis
            eqv = u.spectral()

        return (values * u.Unit(original_units)).to_value(u.Unit(target_units), equivalencies=eqv)


# Set default opacity for data layers to 1 instead of 0.8 in
# some glue-core versions
glue_settings.DATA_ALPHA = 1

# Enable spectrum unit conversion.
glue_settings.UNIT_CONVERTER = 'custom-jdaviz'

custom_components = {'j-tooltip': 'components/tooltip.vue',
                     'j-external-link': 'components/external_link.vue',
                     'j-docs-link': 'components/docs_link.vue',
                     'j-viewer-data-select': 'components/viewer_data_select.vue',
                     'j-viewer-data-select-item': 'components/viewer_data_select_item.vue',
                     'j-layer-viewer-icon': 'components/layer_viewer_icon.vue',
                     'j-tray-plugin': 'components/tray_plugin.vue',
                     'j-play-pause-widget': 'components/play_pause_widget.vue',
                     'j-plugin-section-header': 'components/plugin_section_header.vue',
                     'j-number-uncertainty': 'components/number_uncertainty.vue',
                     'j-plugin-popout': 'components/plugin_popout.vue',
                     'plugin-table': 'components/plugin_table.vue',
                     'plugin-dataset-select': 'components/plugin_dataset_select.vue',
                     'plugin-subset-select': 'components/plugin_subset_select.vue',
                     'plugin-viewer-select': 'components/plugin_viewer_select.vue',
                     'plugin-layer-select': 'components/plugin_layer_select.vue',
                     'plugin-add-results': 'components/plugin_add_results.vue',
                     'plugin-auto-label': 'components/plugin_auto_label.vue',
                     'glue-state-sync-wrapper': 'components/glue_state_sync_wrapper.vue'}

_verbosity_levels = ('debug', 'info', 'warning', 'error')

# Register pure vue component. This allows us to do recursive component instantiation only in the
# vue component file
for name, path in custom_components.items():
    ipyvue.register_component_from_file(None, name,
                                        os.path.join(os.path.dirname(__file__), path))

ipyvue.register_component_from_file('g-viewer-tab', "container.vue", __file__)


class ApplicationState(State):
    """
    The application state object contains all the current front-end state,
    including the loaded data name references, the active viewers, plugins,
    and layout.

    This state object allows for nested callbacks in mutable objects like
    dictionaries and makes it so incremental changes to nested values
    propagate to the traitlet in order to trigger a UI re-render.
    """
    drawer = CallbackProperty(
        False, docstring="State of the plugins drawer.")
    logger_overlay = CallbackProperty(
        False, docstring="State of the logger history overlay.")

    snackbar = DictCallbackProperty({
        'show': False,
        'test': "",
        'color': None,
        'timeout': 3000,
        'loading': False
    }, docstring="State of the quick toast messages.")

    snackbar_queue = SnackbarQueue()

    snackbar_history = ListCallbackProperty(docstring="Previously dismissed snackbar items")

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
        'viewer_labels': True,
        'dense_toolbar': True,
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
        'checktoradial': read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')
    }, docstring="Custom application icons")

    viewer_icons = DictCallbackProperty({}, docstring="Indexed icons (numbers) for viewers across the app")  # noqa
    layer_icons = DictCallbackProperty({}, docstring="Indexed icons (letters) for layers across the app")  # noqa

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
    vdocs = Unicode("").tag(sync=True)
    popout_button = Any().tag(sync=True, **widget_serialization)

    def __init__(self, configuration=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._jdaviz_helper = None
        self._verbosity = 'warning'
        self._history_verbosity = 'info'
        self.popout_button = PopoutButton(self)

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

        # Parse the yaml configuration file used to compose the front-end UI
        self.load_configuration(configuration)

        # If true, link data on load. If false, do not link data to speed up
        # data loading
        self.auto_link = kwargs.pop('auto_link', True)

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

        # Add a fitted_models dictionary that the helpers (or user) can access
        self.fitted_models = {}

        # Internal cache so we don't have to keep calling get_object for the same Data.
        # Key should be (data_label, statistic) and value the translated object.
        self._get_object_cache = {}
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda msg: self._clear_object_cache(msg.subset.label))

        # Add new and inverse colormaps to Glue global state. Also see ColormapRegistry in
        # https://github.com/glue-viz/glue/blob/main/glue/config.py
        new_cms = (['Rainbow', cm.rainbow],
                   ['Seismic', cm.seismic],
                   ['Reversed: Gray', cm.gray_r],
                   ['Reversed: Viridis', cm.viridis_r],
                   ['Reversed: Plasma', cm.plasma_r],
                   ['Reversed: Inferno', cm.inferno_r],
                   ['Reversed: Magma', cm.magma_r],
                   ['Reversed: Hot', cm.hot_r],
                   ['Reversed: Rainbow', cm.rainbow_r])
        for cur_cm in new_cms:
            if cur_cm not in colormaps.members:
                colormaps.add(*cur_cm)

        # Subscribe to messages that result in changes to the layers
        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_layers_changed)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_layers_changed)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=self._on_layers_changed)
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_layers_changed)

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

    def set_style_template_file(self, path):
        """
        Sets the path to a vue file containing a <style> tag that will be applied on top of the
        style defined in ``app.vue``.  This is useful for config-specific or downstream styling
        at the app-level.

        Parameters
        ----------
        path : str or tuple
            Path to a ``.vue`` file containing style rules to inject into the app.
        """
        style_widget = StyleWidget(path)
        self.state.style_widget = "IPY_MODEL_" + style_widget.model_id

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
        self.state.snackbar_queue.put(self.state, msg,
                                      history=msg_level >= history_level,
                                      popup=msg_level >= popup_level)

    def _on_layers_changed(self, msg):
        if hasattr(msg, 'data'):
            layer_name = msg.data.label
        elif hasattr(msg, 'subset'):
            layer_name = msg.subset.label
        else:
            raise NotImplementedError(f"cannot recognize new layer from {msg}")

        if layer_name not in self.state.layer_icons:
            self.state.layer_icons = {**self.state.layer_icons,
                                      layer_name: alpha_index(len(self.state.layer_icons))}

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
        ref_data = dc[reference_data] if reference_data else dc[default_refdata_index]
        linked_data = dc[data_to_be_linked] if data_to_be_linked else dc[-1]

        if 'Trace' in linked_data.meta:
            links = [LinkSame(linked_data.components[1], ref_data.components[0]),
                     LinkSame(linked_data.components[0], ref_data.components[1])]
            dc.add_link(links)
            return
        elif ((self.config in ('specviz2d', 'mosviz') and
               linked_data.meta.get('Plugin', None) is not None) or
              (linked_data.meta.get('Plugin', None) == 'GaussianSmooth' and
               linked_data.ndim < 3 and  # Cube linking requires special logic. See below
               ref_data.ndim < 3)
              ):
            links = [LinkSame(linked_data.components[0], ref_data.components[0]),
                     LinkSame(linked_data.components[1], ref_data.components[1])]
            dc.add_link(links)
            return

        # The glue-astronomy SpectralCoordinates currently seems incompatible with glue
        # WCSLink. This gets around it until there's an upstream fix.
        if isinstance(linked_data.coords, SpectralCoordinates):
            wc_old = ref_data.world_component_ids[-1]
            wc_new = linked_data.world_component_ids[0]
            self.data_collection.add_link(LinkSameWithUnits(wc_old, wc_new))
            return

        try:
            if linked_data.meta.get("Plugin", None) == 'GaussianSmooth':
                raise AttributeError
            dc.add_link(WCSLink(ref_data, linked_data))
        except (AttributeError, IncompatibleWCS):
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
                         ['MomentMap', 'Collapse'])):
                    if pixel_coord == 'z':
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
            try:
                # Properly form path and check if a valid file
                file_obj = pathlib.Path(file_obj)
                if not file_obj.exists():
                    msg_text = "Error: File {} does not exist".format(file_obj)
                    snackbar_message = SnackbarMessage(msg_text, sender=self,
                                                       color='error')
                    self.hub.broadcast(snackbar_message)
                    raise FileNotFoundError("Could not locate file: {}".format(file_obj))
                else:
                    # Convert path to properly formatted string (Parsers do not accept path objs)
                    file_obj = str(file_obj)
            except TypeError:
                # If it's not a str/path type, it might be a compatible class.
                # Pass to parsers to see if they can accept it
                pass

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

    @deprecated(since="3.6", alternative="viz_helper.get_data")
    def get_data_from_viewer(self, viewer_reference, data_label=None,
                             cls='default', include_subsets=True):
        """
        Returns each data component currently rendered within a viewer
        instance. Viewers themselves store a default data type to which the
        Glue data components are transformed upon retrieval. This can be
        optionally overridden with the ``cls`` keyword.

        Notes
        -----
            This is only used in cases where the viewers have been pre-defined
            in the configuration file. Otherwise, viewers are not stored via
            reference.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str, optional
            Optionally provide a label to retrieve a specific data set from the
            viewer instance.
        cls : class
            The class definition the Glue data components get transformed to
            when retrieved. This requires that a working set of translation
            functions exist in the ``glue_astronomy`` package. See
            https://github.com/glue-viz/glue-astronomy for more info.
            If this is the special string ``'default'``,  the ``default_class``
            attribute of the viewer referenced by ``viewer_reference`` is used.
        include_subsets : bool
            Whether to include subset layer data that exists in the viewer but
            has not been included in the core data collection object.

        Returns
        -------
        data : dict
            A dict of the transformed Glue data objects, indexed to
            corresponding viewer data labels.
        """
        viewer = self.get_viewer(viewer_reference)
        cls = viewer.default_class if cls == 'default' else cls

        if cls is not None and not isclass(cls):
            raise TypeError(
                "cls in get_data_from_viewer must be a class, None, or "
                "the 'default' string.")

        data = {}

        # If the viewer also supports collapsing, then grab the user's chosen
        #  statistic for collapsing data
        if hasattr(viewer.state, 'function'):
            statistic = viewer.state.function
        else:
            statistic = None

        for layer_state in viewer.state.layers:
            label = layer_state.layer.label

            if (hasattr(layer_state, 'layer') and
                    (data_label is None or label == data_label)):

                # For raw data, just include the data itself
                if isinstance(layer_state.layer, BaseData):
                    layer_data = layer_state.layer

                    if cls is not None:
                        # If data is one-dimensional, assume that it can be
                        #  collapsed via the defined statistic
                        if 'Trace' in layer_data.meta:
                            layer_data = layer_data.get_object()
                        elif cls == Spectrum1D:
                            layer_data = layer_data.get_object(cls=cls,
                                                               statistic=statistic)
                        else:
                            layer_data = layer_data.get_object(cls=cls)
                    # If the shape of the data is 2d, then use CCDData as the
                    #  output data type
                    elif len(layer_data.shape) == 2:
                        layer_data = layer_data.get_object(cls=CCDData)

                    data[label] = layer_data

                # For subsets, make sure to apply the subset mask to the
                #  layer data first
                elif isinstance(layer_state.layer, Subset):
                    if include_subsets:
                        layer_data = layer_state.layer

                        if cls is not None:
                            handler, _ = data_translator.get_handler_for(cls)
                            try:
                                if cls == Spectrum1D:
                                    # if this is a spectrum, apply the `statistic`:
                                    layer_data = handler.to_object(layer_data,
                                                                   statistic=statistic)
                                else:
                                    # otherwise simply translate to an object:
                                    layer_data = handler.to_object(layer_data)
                            except IncompatibleAttribute:
                                continue

                        data[label] = layer_data

        # If a data label was provided, return only the corresponding data, otherwise return all:
        return data.get(data_label, data)

    @deprecated(since="3.6", alternative="get_subsets")
    def get_subsets_from_viewer(self, viewer_reference, data_label=None, subset_type=None):
        """
        Returns the subsets of a specified viewer converted to astropy regions
        objects.

        It should be noted that the subset translation machinery lives in the
        glue-astronomy repository. Currently, the machinery only works on 2D
        data for cases like range selection. For e.g. a profile viewer that is
        ostensibly just a view into a 3D data set, it is necessary to first
        reduce the dimensions of the data, then retrieve the subset information
        as a regions object. This means that the returned y extents in the
        region are not strictly representative of the subset range in y.

        Parameters
        ----------
        viewer_reference : str
            The reference to the viewer defined with the ``reference`` key
            in the yaml configuration file.
        data_label : str, optional
            Optionally provide a label to retrieve a specific data set from the
            viewer instance.
        subset_type : str, optional
            Optionally specify either "spectral" or "spatial" to return only
            subsets created in a profile (spectrum) viewer or image viewer,
            respectively.

        Returns
        -------
        data : dict
            A dict of the transformed Glue subset objects, with keys
            representing the subset name and values as astropy regions
            objects.
        """
        viewer = self.get_viewer(viewer_reference)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            data = self.get_data_from_viewer(viewer_reference,
                                             data_label,
                                             cls=None)
        regions = {}

        if data_label is not None:
            data = {data_label: data}

        for key, value in data.items():
            if isinstance(value, Subset):
                # Get the component type in a compound subset
                if hasattr(value.subset_state, "state1"):
                    this_type = type(value.subset_state.state1)
                else:
                    this_type = type(value.subset_state)

                # Skip spatial or spectral subsets if only the other is wanted
                if subset_type == "spectral" or isinstance(viewer, BqplotProfileView):
                    if this_type == RoiSubsetState:
                        continue
                elif subset_type == "spatial" or not isinstance(viewer, BqplotProfileView):
                    if this_type == RangeSubsetState:
                        continue

                # Range selection on a profile is currently not supported in
                #  the glue translation machinery for astropy regions, so we
                #  have to do it manually. Only data that is 2d is supported,
                #  therefore, if the data is already 2d, simply use as is.
                if value.data.ndim == 2:
                    region = value.data.get_selection_definition(
                        subset_id=key, format='astropy-regions')
                    regions[key] = region
                    continue

                # There is a special case for 1d data (which is also not
                #  supported currently). We now eschew the use of the
                #  translation machinery entirely and construct the astropy
                #  region ourselves.
                elif value.data.ndim == 1:
                    regions[key] = self.get_subsets(key)
                    continue

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    temp_data = self.get_data_from_viewer(viewer_reference, value.label)
                if isinstance(temp_data, Spectrum1D):
                    regions[key] = self.get_subsets(key)
                    continue

                # Get the pixel coordinate [z] of the 3D data, repeating the
                #  wavelength axis. This doesn't seem strictly necessary as it
                #  returns the same data if the pixel axis is [y] or [x]
                xid = value.data.pixel_component_ids[0]

                # Construct a new data object collapsing over one of the
                #  spatial dimensions. This is necessary because the astropy
                #  region translation machinery in glue-astronomy does not
                #  support non-2D data, even for range objects.
                stat_func = 'median'

                if hasattr(viewer.state, 'function'):
                    stat_func = viewer.state.function

                # Compute reduced data based on the current viewer's statistic
                #  function. This doesn't seem particularly useful, but better
                #  to be consistent.
                reduced_data = Data(x=value.data.compute_statistic(
                    stat_func, value.data.id[xid],
                    subset_state=value.subset_state.copy(), axis=1))

                # Instantiate a new data collection since we need to compose
                #  the collapsed data with the current subset state. We use a
                #  new data collection so as not to inference with the one used
                #  by the application.
                temp_data_collection = DataCollection()
                temp_data_collection.append(reduced_data)

                # Get the data id of the pixel axis that will be used in the
                #  range composition. This is the wavelength axis for the new
                #  2d data.
                xid = reduced_data.pixel_component_ids[1]

                # Create a new subset group to hold our current subset state
                subset_group = temp_data_collection.new_subset_group(
                    label=value.label, subset_state=value.subset_state.copy())

                # Set the subset state axis to the wavelength pixel coordinate
                subset_group.subsets[0].subset_state.att = xid

                # Use the associated collapsed subset data to get an astropy
                #  regions object dependent on the extends of the subset.
                # **Note** that the y values in this region object are not
                #  useful, only the x values are.
                region = subset_group.subsets[0].data.get_selection_definition(
                    format='astropy-regions')
                regions[key] = region

        return regions

    def get_subsets(self, subset_name=None, spectral_only=False,
                    spatial_only=False, object_only=False, simplify_spectral=True,
                    use_display_units=False):
        """
        Returns all branches of glue subset tree in the form that subset plugin can recognize.

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
            Return a composite spectral subset collapsed to a simplified SpectralRegion.
        use_display_units: bool, optional
            Whether to convert to the display units defined in the
            :ref:`Unit Conversion <unit-conversion>` plugin.

        Returns
        -------
        data : dict
            A dict with keys representing the subset name and values as astropy regions
            objects.
        """

        dc = self.data_collection
        subsets = dc.subset_groups

        all_subsets = {}

        for subset in subsets:
            label = subset.label
            if isinstance(subset.subset_state, CompositeSubsetState):
                # Region composed of multiple ROI or Range subset
                # objects that must be traversed
                subset_region = self.get_sub_regions(subset.subset_state,
                                                     simplify_spectral, use_display_units)
            elif isinstance(subset.subset_state, RoiSubsetState):
                # 3D regions represented as a dict including an
                # AstropyRegion object if possible
                subset_region = self._get_roi_subset_definition(subset.subset_state)
            elif isinstance(subset.subset_state, RangeSubsetState):
                # 2D regions represented as SpectralRegion objects
                subset_region = self._get_range_subset_bounds(subset.subset_state,
                                                              simplify_spectral,
                                                              use_display_units)
            else:
                # subset.subset_state can be an instance of MaskSubsetState
                # or something else we do not know how to handle
                all_subsets[label] = None
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
                if object_only and not isinstance(subset_region, SpectralRegion):
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region

            if not (spectral_only or spatial_only) and is_temporal:
                if object_only:
                    all_subsets[label] = [reg['region'] for reg in subset_region]
                else:
                    all_subsets[label] = subset_region

        all_subset_names = [subset.label for subset in dc.subset_groups]
        if subset_name and subset_name in all_subset_names:
            return all_subsets[subset_name]
        elif subset_name:
            raise ValueError(f"{subset_name} not in {all_subset_names}")
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
        elif isinstance(subset_region, list) and len(subset_region) > 0:
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
        viewer = self.get_viewer(self._jdaviz_helper. _default_spectrum_viewer_reference_name)
        data = viewer.data()
        if data and len(data) > 0 and isinstance(data[0], Spectrum1D):
            units = data[0].spectral_axis.unit
        else:
            raise ValueError("Unable to find spectral axis units")
        if use_display_units:
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
                     "subset_state": subset_state}]
        return spec_region

    def _get_roi_subset_definition(self, subset_state):
        # TODO: Imviz: Return sky region if link type is WCS.
        roi_as_region = roi_subset_state_to_region(subset_state)
        return [{"name": subset_state.roi.__class__.__name__,
                 "glue_state": subset_state.__class__.__name__,
                 "region": roi_as_region,
                 "subset_state": subset_state}]

    def get_sub_regions(self, subset_state, simplify_spectral=True, use_display_units=False):

        if isinstance(subset_state, CompositeSubsetState):
            if subset_state and hasattr(subset_state, "state2") and subset_state.state2:
                one = self.get_sub_regions(subset_state.state1,
                                           simplify_spectral, use_display_units)
                two = self.get_sub_regions(subset_state.state2,
                                           simplify_spectral, use_display_units)

                if isinstance(one, list) and "glue_state" in one[0]:
                    one[0]["glue_state"] = subset_state.__class__.__name__

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
                        # Return two first so that we preserve the chronology of how
                        # subset regions are applied.
                        return one + two
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
                        return two + one
                elif subset_state.op is operator.or_:
                    # This covers the ADD subset mode
                    # one + two works for both Range and ROI subsets
                    if one and two:
                        return two + one
                    elif one:
                        return one
                    elif two:
                        return two
                elif subset_state.op is operator.xor:
                    # This covers the ADD subset mode

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
                        new_region = None
                        temp_region = None
                        for subregion in two:
                            # Add all subregions that do not intersect with XOR region
                            # to a new SpectralRegion object
                            if subregion.lower > one.upper or subregion.upper < one.lower:
                                if not new_region:
                                    new_region = subregion
                                else:
                                    new_region += subregion
                            # All other subregions are added to temp_region
                            else:
                                if not temp_region:
                                    temp_region = subregion
                                else:
                                    temp_region += subregion
                        # This is the main application of XOR to other regions
                        if not new_region:
                            new_region = temp_region.invert(one.lower, one.upper)
                        else:
                            new_region = new_region + temp_region.invert(one.lower, one.upper)
                        # This adds the edge regions that are otherwise not included
                        if not (one.lower == temp_region.lower and one.upper == temp_region.upper):
                            new_region = new_region + one.invert(temp_region.lower,
                                                                 temp_region.upper)
                        return new_region
                    else:
                        return two + one
            else:
                # This gets triggered in the InvertState case where state1
                # is an object and state2 is None
                return self.get_sub_regions(subset_state.state1,
                                            simplify_spectral, use_display_units)
        elif subset_state is not None:
            # This is the leaf node of the glue subset state tree where
            # a subset_state is either ROI or Range.
            if isinstance(subset_state, RoiSubsetState):
                return self._get_roi_subset_definition(subset_state)

            elif isinstance(subset_state, RangeSubsetState):
                return self._get_range_subset_bounds(subset_state,
                                                     simplify_spectral, use_display_units)

    def _get_display_unit(self, axis):
        if self._jdaviz_helper is None or self._jdaviz_helper.plugins.get('Unit Conversion') is None:  # noqa
            # fallback on native units (unit conversion is not enabled)
            if axis == 'spectral':
                sv = self.get_viewer(self._jdaviz_helper._default_spectrum_viewer_reference_name)
                return sv.data()[0].spectral_axis.unit
            elif axis == 'flux':
                sv = self.get_viewer(self._jdaviz_helper._default_spectrum_viewer_reference_name)
                return sv.data()[0].flux.unit
            else:
                raise ValueError(f"could not find units for axis='{axis}'")
        try:
            return getattr(self._jdaviz_helper.plugins.get('Unit Conversion')._obj,
                           f'{axis}_unit_selected')
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
        spectral_region = self.get_subsets(subset_name, spectral_only=True)
        if not spectral_region or len(spectral_region) < 2:
            return False
        for index in range(0, len(spectral_region) - 1):
            if spectral_region[index].upper.value >= spectral_region[index + 1].lower.value:
                return True
        return False

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
        spectral_region = self.get_subsets(subset_name, spectral_only=True)
        merged_regions = None
        # Convert SpectralRegion object into a list with tuples representing
        # the lower and upper values of each region.
        reg_as_tup = [(sr.lower.value, sr.upper.value) for sr in spectral_region]
        for index in range(0, len(spectral_region)):
            # Instantiate merged regions
            if not merged_regions:
                merged_regions = [reg_as_tup[index]]
            else:
                last_merged = merged_regions[-1]
                # If the lower value of the current subregion is less than or equal to the upper
                # value of the last subregion added to merged_regions, update last_merged
                # with the max upper value between the two regions.
                if reg_as_tup[index][0] <= last_merged[1]:
                    last_merged = (last_merged[0], max(last_merged[1], reg_as_tup[index][1]))
                    merged_regions = merged_regions[:-1]
                    merged_regions.append(last_merged)
                else:
                    merged_regions.append(reg_as_tup[index])

        new_state = None
        for region in reversed(merged_regions):
            convert_to_range = RangeSubsetState(region[0], region[1], att)
            if new_state is None:
                new_state = convert_to_range
            else:
                new_state = new_state | convert_to_range

        return new_state

    def add_data(self, data, data_label=None, notify_done=True):
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
        notify_done: bool
            Flag controlling whether a snackbar message is set when the data is
            added to the app. Set to False to avoid overwhelming the user if
            lots of data is getting loaded at once.
        """

        if not data_label and hasattr(data, "label"):
            data_label = data.label
        data_label = self.return_unique_name(data_label)
        if data_label in self.data_collection.labels:
            warnings.warn(f"Overwriting existing data entry with label '{data_label}'")

        self.data_collection[data_label] = data

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
            The path to a data file or FITS HDUList or image object or Spectrum1D or
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
        elif isinstance(loaded_object, Spectrum1D):
            data_label = "Spectrum1D"
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

    def return_unique_name(self, data_label, ext=None):
        if data_label is None:
            data_label = "Unknown"

        # This regex checks for any length of characters that end
        # with a space followed by parenthesis with a number inside.
        # If there is a match, the space and parenthesis section will be
        # removed so that the remainder of the label can be checked
        # against the data_label.
        check_if_dup = re.compile(r"(.*)(\s\(\d*\))$")
        labels = self.data_collection.labels
        number_of_duplicates = 0
        max_number = 0
        for label in labels:
            # If label is a duplicate of another label
            if re.fullmatch(check_if_dup, label):
                label_split = label.split(" ")
                label_without_dup = " ".join(label_split[:-1])
                label = label_without_dup
                # Remove parentheses and cast to float
                number_dup = int(label_split[-1][1:-1])
                # Used to keep track the max number of duplicates,
                # even if not all duplicates are loaded (or some
                # are renamed)
                if number_dup > max_number:
                    max_number = number_dup

            if ext and f"{data_label}[{ext}]" == label:
                number_of_duplicates += 1
            elif ext is None and data_label == label:
                number_of_duplicates += 1

        if ext:
            data_label = f"{data_label}[{ext}]"

        if number_of_duplicates > 0:
            data_label = f"{data_label} ({number_of_duplicates})"

        # It is possible to add data named "test (1)" and then
        # add another data named "test" and return_unique_name will see the
        # first test and assume the second is the duplicate, appending
        # "(1)" to the end. This overwrites the original data and
        # causes issues. This block alters the duplicate number to be something unique
        # (one more than the max number duplicate found)
        # if a duplicate is still found in data_collection.
        if data_label in self.data_collection.labels:
            label_split = data_label.split(" ")
            label_without_dup = " ".join(label_split[:-1])
            data_label = f"{label_without_dup} ({max_number + 1})"

        return data_label

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
            not (self.get_viewer("table-viewer").row_selection_in_progress) and
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

        # update data menu entry
        selected_items = viewer_item['selected_data_items']
        data_id = self._data_id_from_label(data_label)
        if data_id in selected_items:
            _ = selected_items.pop(data_id)

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

    def _get_first_viewer_reference_name(
            self, require_no_selected_data=False,
            require_spectrum_viewer=False,
            require_spectrum_2d_viewer=False,
            require_table_viewer=False,
            require_flux_viewer=False,
            require_image_viewer=False
    ):
        """
        Return the viewer reference name of the first available viewer.
        Optionally use ``require_no_selected_data`` to require that the
        viewer has not yet loaded data, or e.g. ``require_spectrum_viewer``
        to require that the viewer supports spectrum visualization.
        """
        from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
        from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
        from jdaviz.configs.cubeviz.plugins.viewers import CubevizProfileView, CubevizImageView
        from jdaviz.configs.mosviz.plugins.viewers import (
            MosvizTableViewer, MosvizProfile2DView
        )

        spectral_viewers = (SpecvizProfileView, CubevizProfileView)
        spectral_2d_viewers = (MosvizProfile2DView, )
        table_viewers = (MosvizTableViewer, )
        image_viewers = (ImvizImageView, CubevizImageView)
        flux_viewers = (CubevizImageView, )

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

        self.hub.broadcast(ViewerRemovedMessage(cid, sender=self))

    def vue_data_item_unload(self, event):
        """
        Callback for selection events in the front-end data list when clicking to unload an entry
        from the viewer.
        """
        data_label = self._get_data_item_by_id(event['item_id'])['name']
        self.remove_data_from_viewer(event['id'], data_label)

    def vue_data_item_visibility(self, event):
        self.set_data_visibility(event['id'],
                                 self._get_data_item_by_id(event['item_id'])['name'],
                                 visible=event['visible'], replace=event.get('replace', False))

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
            Whether to disable the visilility of all other layers in the viewer
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

            [data] = [x for x in self.data_collection if x.label == data_label]

            viewer.add_data(data, percentile=95, color=viewer.color_cycler())
            viewer.set_plot_axes()

            add_data_message = AddDataMessage(data, viewer,
                                              viewer_id=viewer_id,
                                              sender=self)
            self.hub.broadcast(add_data_message)

        # set visibility state of all applicable layers
        for layer in viewer.layers:
            if layer.layer.data.label == data_label:
                if visible and not layer.visible:
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

        # update data menu - selected_data_items should be READ ONLY, not modified by the user/UI
        selected_items = viewer_item['selected_data_items']
        data_id = self._data_id_from_label(data_label)
        selected_items[data_id] = 'visible' if visible else 'hidden'
        if replace:
            for id in selected_items:
                if id != data_id:
                    selected_items[id] = 'hidden'

        # Sets the plot axes labels to be the units of the most recently
        # active data.
        viewer_data_labels = [layer.layer.label for layer in viewer.layers]
        if len(viewer_data_labels) > 0 and getattr(self._jdaviz_helper, '_in_batch_load', 0) == 0:
            # This "if" is nested on purpose to make parent "if" available
            # for other configs in the future, as needed.
            if self.config == 'imviz':
                viewer.on_limits_change()  # Trigger compass redraw

    def vue_data_item_remove(self, event):
        self.data_collection.remove(self.data_collection[event['item_name']])

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

        # TODO: Fix bug with DataCollectionDeleteMessage not working with
        #  a handler in cubeviz/plugins/viewers.py. This code is a temporary
        #  workaround for that.
        if self.config == 'cubeviz':
            viewer = self.get_viewer(self._jdaviz_helper._default_spectrum_viewer_reference_name)
            viewer._check_if_data_removed(msg=msg)

        self._clear_object_cache(msg.data.label)

    @staticmethod
    def _create_data_item(data):
        ndims = len(data.shape)
        wcsaxes = data.meta.get('WCSAXES', None)
        if wcsaxes is None:
            # then we'll need to determine type another way, we want to avoid
            # this when we can though since its not as cheap
            component_ids = [str(c) for c in data.component_ids()]
        if data.label == 'MOS Table':
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
        return {
            'id': str(uuid.uuid4()),
            'name': data.label,
            'locked': False,
            'ndims': data.ndim,
            'type': typ,
            'meta': {k: v for k, v in data.meta.items() if k in ['Plugin', 'mosviz_row']},
            'children': []}

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

    def _create_viewer_item(self, viewer, vid=None, name=None, reference=None):
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

        self.state.viewer_icons.setdefault(vid, len(self.state.viewer_icons)+1)

        return {
            'id': vid,
            'name': name or vid,
            'widget': "IPY_MODEL_" + viewer.figure_widget.model_id,
            'toolbar': "IPY_MODEL_" + viewer.toolbar.model_id if viewer.toolbar else '',  # noqa
            'layer_options': "IPY_MODEL_" + viewer.layer_options.model_id,
            'viewer_options': "IPY_MODEL_" + viewer.viewer_options.model_id,
            'selected_data_items': {},  # noqa data_id: visibility state (visible, hidden, mixed), READ-ONLY
            'visible_layers': {},  # label: {color, label_suffix}, READ-ONLY
            'canvas_angle': 0,  # canvas rotation clockwise rotation angle in deg
            'canvas_flip_horizontal': False,  # canvas rotation horizontal flip
            'config': self.config,  # give viewer access to app config/layout
            'data_open': False,
            'collapse': True,
            'reference': reference}

    def _on_new_viewer(self, msg, vid=None, name=None):
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

        Returns
        -------
        viewer : `~glue_jupyter.bqplot.common.BqplotBaseView`
            The new viewer instance.
        """
        viewer = self._application_handler.new_data_viewer(
            msg.cls, data=msg.data, show=False)
        viewer.figure_widget.layout.height = '100%'

        if hasattr(viewer.state, 'linked_by_wcs'):
            links_control_plugin = self._jdaviz_helper.plugins.get('Links Control', None)
            if links_control_plugin is not None:
                viewer.state.linked_by_wcs = links_control_plugin.link_type.selected == 'WCS'
            elif len(self._viewer_store):
                # The plugin would only not exist for instances of Imviz where the user has
                # intentionally removed the Links Control plugin, but in that case we will
                # adopt "linked_by_wcs" from the first (assuming all are the same)
                # NOTE: deleting the default viewer is forbidden both by API and UI, but if
                # for some reason that was the case here, linked_by_wcs will default to False
                viewer.state.linked_by_wcs = list(self._viewer_store.values())[0].state.linked_by_wcs  # noqa

        if msg.x_attr is not None:
            x = msg.data.id[msg.x_attr]
            viewer.state.x_att = x

        # Create the viewer item dictionary
        if name is None:
            name = vid
        new_viewer_item = self._create_viewer_item(
            viewer=viewer, vid=vid, name=name, reference=name
        )

        new_stack_item = self._create_stack_item(
            container='gl-stack',
            viewers=[new_viewer_item])

        # Store the glupyter viewer object so we can access the add and remove
        #  data methods in the future
        vid = new_viewer_item['id']
        self._viewer_store[vid] = viewer

        # Add viewer locally
        self.state.stack_items.append(new_stack_item)

        self.session.application.viewers.append(viewer)

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
        self.config = config['settings'].get('configuration', 'unknown')
        self.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

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

        for name in config.get('tray', []):
            tray = tray_registry.members.get(name)
            tray_registry_options = tray.get('viewer_reference_name_kwargs', {})

            # Optional keyword arguments are required to initialize some
            # tray items. These kwargs specify the viewer reference names that are
            # assumed to be present in the configuration.
            optional_tray_kwargs = dict()

            # If viewer reference names need to be passed to the tray item
            # constructor, pass the names into the constructor in the format
            # that the tray items expect.
            for opt_attr, [opt_kwarg, get_name_kwargs] in tray_registry_options.items():
                opt_value = getattr(
                    self, opt_attr, self._get_first_viewer_reference_name(**get_name_kwargs)
                )

                if opt_value is None:
                    continue

                optional_tray_kwargs[opt_kwarg] = opt_value

            tray_item_instance = tray.get('cls')(
                app=self, **optional_tray_kwargs
            )
            tray_item_label = tray.get('label')
            # store a copy of the tray name in the instance so it can be accessed by the
            # plugin itself
            tray_item_instance._plugin_name = tray_item_label

            self.state.tray_items.append({
                'name': name,
                'label': tray_item_label,
                'widget': "IPY_MODEL_" + tray_item_instance.model_id
            })

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

    def get_tray_item_from_name(self, name):
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
        from ipywidgets.widgets import widget_serialization

        tray_item = None
        for item in self.state.tray_items:
            if item['name'] == name or item['label'] == name:
                ipy_model_id = item['widget']
                tray_item = widget_serialization['from_json'](ipy_model_id, None)
                break

        if tray_item is None:
            raise KeyError(f'{name} not found in app.state.tray_items')

        return tray_item
