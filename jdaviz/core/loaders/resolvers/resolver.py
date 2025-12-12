import os
import warnings
from contextlib import contextmanager
from functools import cached_property
from traitlets import Bool, Float, Instance, List, Unicode, observe, default
from ipywidgets import widget_serialization

from glue_jupyter.common.toolbar_vuetify import read_icon
from astropy.coordinates import SkyCoord
from astropy.coordinates.builtin_frames import __all__ as all_astropy_frames
from astropy.table import Table as astropyTable
from astroquery.mast import MastMissions

from jdaviz.core.custom_traitlets import FloatHandleEmpty, IntHandleEmpty
from jdaviz.core.events import (AddDataMessage,
                                RemoveDataMessage,
                                SnackbarMessage,
                                FootprintOverlayClickMessage,
                                LinkUpdatedMessage,
                                ViewerAddedMessage)
from jdaviz.core.marks import RegionOverlay
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        Table,
                                        CustomToolbarToggleMixin,
                                        UnitSelectPluginComponent,
                                        ViewerSelect,
                                        with_spinner,
                                        _is_image_viewer)
from jdaviz.core.registries import (loader_resolver_registry,
                                    loader_parser_registry,
                                    loader_importer_registry)
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.region_translators import is_stcs_string, stcs_string2region
from jdaviz.utils import download_uri_to_path, find_closest_polygon_mark, layer_is_image_data
from glue.core.message import DataCollectionAddMessage, DataCollectionDeleteMessage


__all__ = ['BaseResolver', 'BaseConeSearchResolver', 'find_matching_resolver']


class FormatSelect(SelectPluginComponent):
    """
    Select component for the format field of a resolver.

    Parameters
    ----------
    plugin
        the parent plugin object
    items : str
        the name of the items traitlet defined in ``plugin``
    selected : str
        the name of the selected traitlet defined in ``plugin``
    default_mode : str, optional
        What mode to use when making the default selection.  Valid options: first, default_text,
        empty.
    """
    debug = Bool(False).tag(sync=True)
    _parsers = {}
    _importers = {}

    def __init__(self, plugin, items, selected, default_mode='first'):
        self._invalid_importers = {}
        self._importers = {}
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    @observe('filters', 'debug')
    def _update_items(self, msg={}):
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        all_formats = []
        self._parsers = {}
        self._dbg_importers = {}
        self._invalid_importers = {}
        self._importers = {}

        # check for valid parser > importer combinations given the current filters
        # and resolver inputs
        try:
            # NOTE: plugin is just because this inherits from SelectPluginComponent,
            # but is actually the resolver.  This calls the implemented __call__ method
            # on the parent resolver.
            parser_input = self.plugin.output
        except Exception as e:
            self.items = []
            self._invalid_importers = f'resolver exception: {e}'
            self._apply_default_selection()
            return

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for parser_name, Parser in loader_parser_registry.members.items():
                this_parser = Parser(self.plugin.app, parser_input)
                self._parsers[parser_name] = this_parser
                try:
                    if this_parser.is_valid:
                        importer_input = this_parser.output
                    else:
                        self._invalid_importers[parser_name] = 'not valid'
                        importer_input = None
                except Exception as e:
                    self._invalid_importers[parser_name] = f'parser exception: {e}'
                    importer_input = None

                if importer_input is None:
                    self._invalid_importers.setdefault(parser_name, 'importer_input is None')
                    this_parser._cleanup()
                    continue
                for importer_name, Importer in loader_importer_registry.members.items():
                    label = f"{parser_name} > {importer_name}"
                    if self.plugin._restrict_to_formats is not None and \
                            importer_name not in self.plugin._restrict_to_formats:
                        self._invalid_importers[label] = 'not matching format restriction'  # noqa
                        continue
                    try:
                        this_importer = Importer(app=self.plugin.app,
                                                 resolver=self.plugin,
                                                 parser=this_parser,
                                                 input=importer_input)
                    except Exception as e:  # nosec
                        self._invalid_importers[label] = f'importer exception: {e}'
                        continue
                    if self.debug:
                        self._dbg_importers[label] = this_importer
                    if (self.plugin._restrict_to_target is not None and
                            this_importer.target.get('label') != self.plugin._restrict_to_target):
                        # skip importers that do not match the target
                        self._invalid_importers[label] = 'not matching target'
                        continue
                    if this_importer.is_valid:
                        if self._is_valid_item(this_importer):
                            item = {'label': importer_name,
                                    'parser': parser_name,
                                    'importer': importer_name,
                                    'target': this_importer.target}
                            parser_pref = this_importer.parser_preference
                            if importer_name not in self._importers:
                                all_formats.append(item)
                                self._importers[importer_name] = this_importer
                            elif not len(parser_pref) or parser_name not in parser_pref:
                                # default to the previous (or first) found match
                                continue
                            else:
                                # then there was already a match from an earlier parser.  Compare
                                # to see which has preference and replace if necessary.
                                item_importers = [i['importer'] for i in all_formats]
                                item_index = item_importers.index(importer_name)
                                prev_parser = all_formats[item_index]['parser']
                                parser_pref = this_importer.parser_preference
                                if (prev_parser not in parser_pref or
                                        parser_pref.index(prev_parser) > parser_pref.index(parser_name)):  # noqa
                                    # this parser has preference over the previous one
                                    all_formats[item_index] = item
                                    self._importers[importer_name] = this_importer
                                else:
                                    # this previous parser has preference over this one
                                    continue

                        else:
                            # we'll store the importer even if it isn't valid according to the
                            # filters so that they can be used when compiling the list of
                            # target filters
                            self._importers[importer_name] = this_importer
                    else:
                        self._invalid_importers[label] = 'not valid'

        self.items = all_formats
        self._apply_default_selection()


class TargetSelect(SelectPluginComponent):
    """
    Select component for the target (filter on format) of a resolver.

    Parameters
    ----------
    plugin
        the parent plugin object
    items : str
        the name of the items traitlet defined in ``plugin``
    selected : str
        the name of the selected traitlet defined in ``plugin``
    default_mode : str, optional
        What mode to use when making the default selection.  Valid options: first, default_text,
        empty.
    """

    def __init__(self, plugin, items, selected, default_mode='first'):
        self._importers = {}
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    def set_filter_target_in(self, targets):
        def filter_factory(targets):
            def filter_target(item):
                return item['label'] in targets
            return filter_target
        self.filters = [filter_factory(targets)]

    @observe('filters')
    def _update_items(self, msg={}):
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        # loop through choices on format and compile list of targets
        # note that the selection of a target may affect the available formats
        # so we want to store all importers in the target select even if they are not valid there
        # and use that list when compiling list of valid targets
        all_targets = []
        for importer in self.plugin.format._importers.values():
            target = importer.target
            if target not in all_targets:
                all_targets.append(target)

        self.items = [{'label': 'Any'}] + [item for item in all_targets if self._is_valid_item(item)]  # noqa
        self._apply_default_selection()


class BaseResolver(PluginTemplateMixin, CustomToolbarToggleMixin):
    _defer_resolver_input_updated = False  # noqa: only use via defer_resolver_input_updated context manager
    default_input = None
    default_input_cast = None
    requires_api_support = False

    spinner = Unicode("").tag(sync=True)

    parsed_input_is_empty = Bool(True).tag(sync=True)

    # whether the current output could be interpretted as a list of data products
    parsed_input_is_query = Bool(False).tag(sync=True)
    # if parsed_input_is_query is True, whether to treat it as such
    # or pass it on directly to the parsers/importers
    treat_table_as_query = Bool(True).tag(sync=True)

    observation_table = Instance(Table).tag(sync=True, **widget_serialization)
    observation_table_populated = Bool(False).tag(sync=True)
    file_table = Instance(Table).tag(sync=True, **widget_serialization)
    file_table_populated = Bool(False).tag(sync=True)

    # options to download selected item in products list
    file_cache = Bool(True).tag(sync=True)
    file_local_path = Unicode("./").tag(sync=True)
    file_timeout = FloatHandleEmpty(10).tag(sync=True)

    importer_widget = Unicode().tag(sync=True)

    # Set remote server options based on the app configuration
    # read-only: change via app.state.settings['server_is_remote']
    server_is_remote = Bool(False).tag(sync=True)

    format_items = List().tag(sync=True)
    format_selected = Unicode().tag(sync=True)
    valid_import_formats = Unicode().tag(sync=True)

    target_items = List().tag(sync=True)
    target_selected = Unicode().tag(sync=True)

    is_wcs_linked = Bool(False).tag(sync=True)
    image_data_loaded = Bool(False).tag(sync=True)
    footprint_select_icon = Unicode(read_icon(os.path.join(
        ICON_DIR, 'footprint_select.svg'), 'svg+xml')).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self.set_active_loader_callback = kwargs.pop('set_active_loader_callback', None)
        self.open_callback = kwargs.pop('open_callback', None)
        self.close_callback = kwargs.pop('close_callback', None)
        self._restrict_to_target = kwargs.pop('restrict_to_target', None)

        super().__init__(*args, **kwargs)

        self.observation_table.enable_clear = False
        self.observation_table.show_if_empty = False
        self.observation_table.show_rowselect = True
        self.observation_table.item_key = "Dataset"
        self.observation_table.multiselect = True
        self.observation_table._selected_rows_changed_callback = self.on_observation_select_changed

        self.file_table.enable_clear = False
        self.file_table.show_if_empty = False
        self.file_table.show_rowselect = True
        self.file_table.item_key = "url"
        self.file_table.multiselect = False
        self.file_table._selected_rows_changed_callback = self.on_file_select_changed

        # Setup footprint selection
        if self.app is not None:
            self.is_wcs_linked = getattr(self.app, '_align_by', None) == 'wcs'
            self.app.hub.subscribe(self, FootprintOverlayClickMessage,
                                   handler=self._on_region_select)
            self.image_data_loaded = any(layer_is_image_data(data)
                                         for data in self.app.data_collection)
            self.app.hub.subscribe(self, DataCollectionAddMessage,
                                   handler=self._on_collection_data_added)
            self.app.hub.subscribe(self, DataCollectionDeleteMessage,
                                   handler=self._on_data_removed)
            self.app.hub.subscribe(self, LinkUpdatedMessage,
                                   handler=self._on_link_type_updated)
            self.app.hub.subscribe(self, ViewerAddedMessage,
                                   handler=self._on_viewer_added)
            self.app.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_viewer_data_added)

        def custom_toolbar(viewer):
            if (self.parsed_input_is_query and self.treat_table_as_query and
                    's_region' in self.observation_table.headers_avail):
                return viewer.toolbar._original_tools_nested[:3] + [['jdaviz:selectregion']], 'jdaviz:selectregion'  # noqa: E501
            return None, None

        self.custom_toolbar.callable = custom_toolbar
        self.custom_toolbar.name = "Footprint Selection"

        # subclasses should call self._resolver_input_updated on any change
        # to user-inputs that might affect the available formats
        self.format = FormatSelect(self,
                                   items='format_items',
                                   selected='format_selected')
        self._restrict_to_formats = kwargs.get('format', None)
        if isinstance(self._restrict_to_formats, str):
            self._restrict_to_formats = [self._restrict_to_formats]

        self.target = TargetSelect(self,
                                   items='target_items',
                                   selected='target_selected')

        # Ensure traitlet and app state are in sync at init
        self.server_is_remote = self.app.state.settings.get('server_is_remote',
                                                            self.server_is_remote)

        # Set up bidirectional synchronization
        # Listen for changes to app.state.settings and update traitlet
        self.app.state.add_callback('settings', self._on_app_settings_changed)

    def vue_link_by_wcs(self, *args):
        plg = self.app._jdaviz_helper.plugins.get('Orientation', None)
        if plg is not None:
            plg.align_by = 'WCS'
        self.is_wcs_linked = True

    @default('observation_table')
    def _default_observation_table(self):
        return Table(self,
                     name='observation_table',
                     title='Observations')

    @default('file_table')
    def _default_file_table(self):
        return Table(self,
                     name='file_table',
                     title='Files')

    def _on_app_settings_changed(self, new_settings_dict):
        """
        Update traitlet when app state settings change.

        Parameters
        ----------
        new_settings_dict : dict
            The new settings dictionary from the app state.
        """
        self.server_is_remote = new_settings_dict.get('server_is_remote', False)

    def _on_collection_data_added(self, msg):
        self.image_data_loaded = any(layer_is_image_data(data) for data in self.app.data_collection)

    def _on_viewer_data_added(self, msg):
        """
        If footprint selection is enabled and this is an image viewer
        with valid WCS, add footprints to this viewer.
        """

        if not self.custom_toolbar_enabled:
            return
        if not (self.parsed_input_is_query and self.treat_table_as_query):
            return
        if 's_region' not in self.observation_table.headers_avail:
            return
        # Get the viewer from the message
        if not hasattr(msg, 'viewer_id') or msg.viewer_id is None:
            return

        viewer = self.app.get_viewer_by_id(msg.viewer_id)
        if viewer is None:
            return
        # Check if it's an image viewer
        if not _is_image_viewer(viewer):
            return
        # Does this viewer already have footprints? If so, don't re-add.
        existing_labels = [
            mark.label for mark in viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]
        if existing_labels:
            return
        # Check for valid WCS
        if (not hasattr(viewer.state, "reference_data") or
            viewer.state.reference_data is None or
            not hasattr(viewer.state.reference_data, "coords") or
                viewer.state.reference_data.coords is None):
            # No WCS yet; nothing to do
            return
        self._add_footprints_to_viewer(viewer)

    def _on_data_removed(self, msg):
        self.image_data_loaded = any(layer_is_image_data(data) for data in self.app.data_collection)

    def _on_link_type_updated(self, msg=None):
        self.is_wcs_linked = getattr(self.app, '_align_by', None) == 'wcs'

    @contextmanager
    def defer_resolver_input_updated(self):
        """
        Context manager to delay updating format items until multiple traitlets have been set.
        """
        self._defer_resolver_input_updated = True
        try:
            yield
        finally:
            self._defer_resolver_input_updated = False
            self._resolver_input_updated()

    @classmethod
    def from_input(cls, app, inp, format=None, **kwargs):
        self = cls(app=app, format=format)
        if self.default_input is None:
            raise NotImplementedError("Resolver subclass must implement default_input")  # noqa pragma: nocover
        with self.defer_resolver_input_updated():
            setattr(self, self.default_input,
                    self.default_input_cast(inp) if self.default_input_cast else inp)
            user_api = self.user_api
            for k, v in kwargs.items():
                if hasattr(user_api, k):
                    setattr(user_api, k, v)
        return self

    @property
    def is_valid(self):
        # override by subclass
        return False  # pragma: nocover

    @property
    def input(self):
        if self.default_input is None:
            raise NotImplementedError("Resolver subclass must implement default_input")
        return getattr(self, self.default_input)

    def parse_input(self):
        # override by subclass - this should return something that is either interpreted as
        # a products list OR something that can be passed to at least one parser
        raise NotImplementedError("Resolver subclass must implement parse_input")  # pragma: nocover

    @cached_property
    def parsed_input(self):
        return self.parse_input()

    def _parsed_input_to_table(self, parsed_input):
        if (isinstance(parsed_input, str)
                and os.path.exists(parsed_input) and os.path.isfile(parsed_input)):
            # try to read into a table which could be a products list
            try:
                parsed_input = astropyTable.read(parsed_input)
            except Exception:  # nosec
                return None
        if isinstance(parsed_input, astropyTable):
            return parsed_input
        return None

    def _parsed_input_to_observation_table(self, parsed_input_table):
        if 'Dataset' in parsed_input_table.colnames:
            return parsed_input_table
        for map_to_ds in ('fileSetName', 'sci_data_set_name'):
            if map_to_ds in parsed_input_table.colnames:
                parsed_input_table.rename_column(map_to_ds, 'Dataset')
                return parsed_input_table
        return None

    def _parsed_input_to_file_table(self, parsed_input_table):
        if 'url' in parsed_input_table.colnames:
            return parsed_input_table
        for map_to_url in ('URL', 'uri', 'URI', 'dataURI', 'download', 'Filename'):
            if map_to_url in parsed_input_table.colnames:
                parsed_input_table.rename_column(map_to_url, 'url')
                return parsed_input_table
        return None

    def _cleanup(self):
        # clear the existing cache and close any open file references
        # from referenced parsers/importers
        for parser in self.format._parsers.values():
            parser._cleanup()
        for importer in self.format._importers.values():
            if hasattr(importer, '_cleanup'):
                importer._cleanup()
        self._clear_cache('parsed_input', 'output')

    @observe('parsed_input_is_query', 'treat_table_as_query')
    @with_spinner('spinner', 'parsing input...')
    def _resolver_input_updated(self, msg={}):
        if self._defer_resolver_input_updated:
            return
        if msg.get('name') == 'treat_table_as_query':
            # the input itself has remain unchanged, but how that
            # is mapped to output has
            self._clear_cache('output')
        else:
            self._cleanup()

        try:
            parsed_input = self.parsed_input  # calls self.parse_input() on the subclass and caches
        except Exception:  # nosec
            self.parsed_input_is_empty = True
            self.parsed_input_is_query = False
            self.observation_table_populated = False
            self.file_table_populated = False
            self.observation_table._clear_table()
            self.file_table._clear_table()
            self._update_format_items()
            return

        if parsed_input is None or getattr(parsed_input, 'len', lambda: 1)() == 0:
            self.parsed_input_is_empty = True
            self.parsed_input_is_query = False
            self.observation_table_populated = False
            self.file_table_populated = False
            self.observation_table._clear_table()
            self.file_table._clear_table()
            self._update_format_items()
            return

        # first attempt to parse the input as a table
        parsed_input_table = self._parsed_input_to_table(parsed_input)
        # if the input could be parsed as a table, try to interpret it as
        # either an observation table or file table.  parsed_input_table
        # will be None if it could not be parsed as a table.
        if parsed_input_table is not None:
            file_table = self._parsed_input_to_file_table(parsed_input_table)
            if file_table is not None:
                self.observation_table._clear_table()
                self.file_table._clear_table()

                for row in file_table:
                    self.file_table.add_item(row)
                self.parsed_input_is_query = True
                self.observation_table_populated = False
                self.file_table_populated = True
                return

            observation_table = self._parsed_input_to_observation_table(parsed_input_table)
            if observation_table is not None:
                self.observation_table._clear_table()
                self.file_table._clear_table()

                for row in observation_table:
                    self.observation_table.add_item(row)
                self.parsed_input_is_query = True
                self.observation_table_populated = True
                self.file_table_populated = False
                return

        self.parsed_input_is_empty = False
        self.parsed_input_is_query = False
        self.observation_table_populated = False
        self.file_table_populated = False
        self._update_format_items()

    @cached_property
    def missions_query(self):
        return MastMissions()

    @with_spinner('spinner', 'fetching product list...')
    def _get_product_list(self, mission, dataset):
        self.missions_query.mission = mission
        return self.missions_query.get_product_list(dataset)

    @staticmethod
    def guess_mission(dataset):
        if dataset.startswith('jw'):
            return 'jwst'
        elif dataset.startswith('r'):
            return 'roman'
        else:
            return 'hst'

    def on_observation_select_changed(self, _=None):
        # Sync footprint selection across all viewers (only if footprints are displayed)
        if self.custom_toolbar_enabled and self.parsed_input_is_query and self.treat_table_as_query:
            self._sync_footprint_selection_to_viewers()
        # Fetch products if rows are selected
        if len(self.observation_table.selected_rows) == 0:
            self.app.hub.broadcast(SnackbarMessage("No observation currently selected",
                                                   sender=self, color="warning"))
        else:
            datasets = [row['Dataset'] for row in self.observation_table.selected_rows]
            results = self._get_product_list(self.guess_mission(datasets[0]), datasets)
            file_table = self._parsed_input_to_file_table(results)
            if file_table is not None:
                self.file_table._clear_table()
                for row in file_table:
                    self.file_table.add_item(row)
                self.file_table_populated = True
            else:
                self.app.hub.broadcast(SnackbarMessage(f"No products found for {datasets}",
                                                       sender=self, color="error"))
                self.file_table_populated = False

    def _get_image_viewers(self):
        return [viewer for viewer in self.app._viewer_store.values()
                if _is_image_viewer(viewer)]

    def toggle_custom_toolbar(self):
        """Override to control footprint display when toolbar is toggled."""
        if not self.custom_toolbar_enabled:
            if self.parsed_input_is_query and self.treat_table_as_query:
                self._display_observation_footprints()
            super().toggle_custom_toolbar()
        else:
            super().toggle_custom_toolbar()
            if self.parsed_input_is_query and self.treat_table_as_query:
                self._remove_observation_footprints()

    @observe('custom_toolbar_enabled')
    def _on_custom_toolbar_enabled_changed(self, change={}):
        if not change.get('new', self.custom_toolbar_enabled):
            # Toolbar was disabled - remove footprints from all viewers
            if self.parsed_input_is_query and self.treat_table_as_query:
                self._remove_observation_footprints()

    def _on_region_select(self, msg):
        """Handle footprint click events."""
        if not (self.parsed_input_is_query and self.treat_table_as_query):
            return

        click_viewer = msg.sender.viewer if hasattr(msg.sender, 'viewer') else None
        if click_viewer is None:
            return
        region_marks = [
            mark for mark in click_viewer.figure.marks
            if isinstance(mark, RegionOverlay)
        ]

        click_x, click_y = msg.x, msg.y
        selected_idx = find_closest_polygon_mark(click_x, click_y, region_marks)

        if selected_idx is not None:
            currently_selected = set()
            for row in self.observation_table.selected_rows:
                idx = self.observation_table.items.index(row)
                currently_selected.add(idx)

            # Toggle selection
            if selected_idx in currently_selected:
                currently_selected.discard(selected_idx)
            else:
                currently_selected.add(selected_idx)

            # Update the table selection
            if currently_selected:
                self.observation_table.select_rows(sorted(list(currently_selected)))
            else:
                # Clear selection
                self.observation_table.selected_rows = []

    def _display_observation_footprints(self):
        if 's_region' not in self.observation_table.headers_avail:
            return

        image_viewers = self._get_image_viewers()
        if not image_viewers:
            return
        regions = []
        region_labels = []
        for idx, row in enumerate(self.observation_table.items):
            s_region_str = row.get('s_region', '')

            if not s_region_str or (isinstance(s_region_str, str) and s_region_str.strip() == ''):
                continue
            if not is_stcs_string(s_region_str):
                continue
            region = stcs_string2region(s_region_str)
            regions.append(region)
            region_labels.append(idx)

        if not regions:
            return

        for viewer in image_viewers:
            viewer._add_region_overlay(
                region=regions,
                region_label=region_labels,
                selected=False,
                fill_opacities=[0]
            )

        self._sync_footprint_selection_to_viewers()

    def _remove_observation_footprints(self):
        """Remove all observation footprints from all image viewers."""
        image_viewers = self._get_image_viewers()
        if not image_viewers:
            return

        # Get all labels (row indices) from observation table
        all_labels = []
        for idx, row in enumerate(self.observation_table.items):
            s_region_str = row.get('s_region', '')
            if not s_region_str or (isinstance(s_region_str, str) and s_region_str.strip() == ''):
                continue
            if not is_stcs_string(s_region_str):
                continue
            all_labels.append(idx)

        if not all_labels:
            return

        # Remove footprints from all viewers
        for viewer in image_viewers:
            # Only remove labels that actually exist in this viewer
            existing_labels = [
                mark.label for mark in viewer.figure.marks
                if isinstance(mark, RegionOverlay)
            ]
            labels_to_remove = [label for label in all_labels if label in existing_labels]
            if labels_to_remove:
                viewer._remove_region_overlay(region_label=labels_to_remove)

    def _sync_footprint_selection_to_viewers(self):
        """Sync footprint selection state across all viewers based on table selection."""
        image_viewers = self._get_image_viewers()
        if not image_viewers:
            return

        selected_indices = set()
        for row in self.observation_table.selected_rows:
            idx = self.observation_table.items.index(row)
            selected_indices.add(idx)

        valid_labels = []
        for idx, row in enumerate(self.observation_table.items):
            s_region_str = row.get('s_region', '')
            if not s_region_str or (isinstance(s_region_str, str) and s_region_str.strip() == ''):
                continue
            if not is_stcs_string(s_region_str):
                continue
            valid_labels.append(idx)

        # Update selection in all viewers
        for viewer in image_viewers:
            for label in valid_labels:
                if label in selected_indices:
                    viewer._select_region_overlay(region_label=label)
                else:
                    viewer._deselect_region_overlay(region_label=label)

    def _on_viewer_added(self, msg):
        """When a new viewer is created, add footprints if toolbar is enabled."""
        if not self.custom_toolbar_enabled:
            return
        if not (self.parsed_input_is_query and self.treat_table_as_query):
            return

        viewer = self.app.get_viewer_by_id(msg.viewer_id)
        if viewer is None:
            return
        # Check if it's an image viewer
        if not _is_image_viewer(viewer):
            return
        if 's_region' not in self.observation_table.headers_avail:
            return
        # Check if viewer has valid WCS before attempting to add footprints
        # New viewers may not have data/WCS yet, so we skip and wait for AddDataMessage
        if (not hasattr(viewer.state, 'reference_data') or
            viewer.state.reference_data is None or
            not hasattr(viewer.state.reference_data, 'coords') or
                viewer.state.reference_data.coords is None):
            # No WCS yet - footprints will be added later when data is loaded
            # via _on_viewer_data_added handler
            return
        # Viewer has WCS, safe to add footprints
        self._add_footprints_to_viewer(viewer)

    def _add_footprints_to_viewer(self, viewer):
        # Build regions from table
        regions = []
        region_labels = []
        for idx, row in enumerate(self.observation_table.items):
            s_region_str = row.get('s_region', '')
            if not s_region_str or (isinstance(s_region_str, str) and s_region_str.strip() == ''):
                continue
            if not is_stcs_string(s_region_str):
                continue
            region = stcs_string2region(s_region_str)
            regions.append(region)
            region_labels.append(idx)

        if not regions:
            return
        viewer._add_region_overlay(
            region=regions,
            region_label=region_labels,
            selected=False,
            fill_opacities=[0]
        )
        # Sync selection state with table
        self._sync_footprint_selection_to_viewers()

    def on_file_select_changed(self, _=None):
        self._clear_cache('output')
        self._update_format_items()

    @with_spinner('spinner', 'searching for valid formats...')
    def _update_format_items(self):
        # NOTE: this will call self.output
        self.format._update_items()
        self.target._update_items()  # assumes format._importers is updated from above
        # ensure the importer updates even if the format selection remains fixed
        self._on_format_selected_changed()

    def get_selected_url(self):
        if len(self.file_table.selected_rows) != 1:
            return None
        url = self.file_table.selected_rows[0]['url']
        if not url.startswith(('http://', 'https://', 'mast:', 'ftp:', 's3:')):
            return f'https://mast.stsci.edu/search/{self.guess_mission(url)}/api/v0.1/retrieve_product?product_name={url}'  # noqa
        return url

    @with_spinner('spinner', 'downloading file...')
    def _download_from_file_table(self):
        url = self.get_selected_url().strip()
        if not url:
            return None
        return download_uri_to_path(url,
                                    cache=self.file_cache,
                                    local_path=self.file_local_path,
                                    timeout=self.file_timeout)

    @cached_property
    def output(self):
        if self.parsed_input_is_query and self.treat_table_as_query:
            return self._download_from_file_table()
        else:
            return self.parsed_input

    @property
    def user_api(self):
        return LoaderUserApi(self)

    @property
    def default_label(self):
        # override by subclass to provide a default label to the importer
        # importers can then decide whether to use this or not.
        return None

    @property
    def parser(self):
        # give access to the parser used by the selected importer
        return self.importer._parser

    @property
    def importer(self):
        # give access to the importer defined by the user-selection on format
        if not self.format.selected:
            raise ValueError("must select a format before accessing importer")
        return self.format._importers[self.format.selected]

    def load(self):
        """
        Import into jdaviz with all selected options.
        """
        return self.importer()

    @observe('target_selected')
    def _on_target_selected_changed(self, change={}):
        def matches_target_factory(target):
            def matches_target(importer):
                return importer.target.get('label', '') == target
            return matches_target

        if self._restrict_to_target is not None:
            self.format.filters = [matches_target_factory(self._restrict_to_target)]
        elif self.target_selected == 'Any':
            self.format.filters = []
        else:
            self.format.filters = [matches_target_factory(self.target_selected)]

    def _get_valid_import_formats(self):
        if self._restrict_to_target is not None:
            # if the resolver was initialized with a list of valid import formats,
            # use that instead of the registry
            return [self._restrict_to_target]
        # fallback on all items available in the registry
        return loader_importer_registry.members.keys()

    @observe('format_selected')
    def _on_format_selected_changed(self, change={}):
        if self.format_selected == '':
            self.importer_widget = ''

            if (hasattr(self.format._invalid_importers, 'keys') and
               self.format._invalid_importers.keys()) and self.target_selected:
                # if no valid importer for format_selected, provide supported sources/formats
                # to user in a warning message
                self.valid_import_formats = ", ".join(self._get_valid_import_formats())
        else:
            self.importer_widget = "IPY_MODEL_" + self.importer.model_id
            self.valid_import_formats = ''

            self.importer.reset_and_check_existing_data_in_dc()

    def close_in_tray(self, close_sidebar=False):
        """
        Close the loader in the sidebar/tray.

        Parameters
        ----------
        close_sidebar : bool
            Whether to also close the sidebar itself.
        """
        if self.close_callback is not None:
            self.close_callback()
        if close_sidebar:
            self.app.state.drawer_content = ''

    def open_in_tray(self):
        """
        Show this resolver in the sidebar tray.
        """
        if self.set_active_loader_callback is None:
            raise NotImplementedError("set_active_loader_callback must be set to open dialog to specific tab")  # noqa
        self.set_active_loader_callback(self._registry_label)
        if self.open_callback is not None:
            self.open_callback()


class BaseConeSearchResolver(BaseResolver):
    viewer_items = List([]).tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)

    source = Unicode("").tag(sync=True)
    coord_follow_viewer_pan = Bool(False).tag(sync=True)
    viewer_centered = Bool(False).tag(sync=True)
    coordframe_choices = List([]).tag(sync=True)
    coordframe_selected = Unicode("icrs").tag(sync=True)
    radius = Float(1).tag(sync=True)
    radius_unit_items = List().tag(sync=True)
    radius_unit_selected = Unicode("deg").tag(sync=True)

    max_results = IntHandleEmpty(1000).tag(sync=True)
    returned_no_results = Bool(False).tag(sync=True)
    returned_max_results = Bool(False).tag(sync=True)

    results_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output = None

        self.viewer = ViewerSelect(
            self, "viewer_items", "viewer_selected", manual_options=["Manual"],
            filters=['is_image_viewer']
        )

        self.coordframe = SelectPluginComponent(
            self, items="coordframe_choices", selected="coordframe_selected"
        )
        self.coordframe.choices = [frame.lower() for frame in all_astropy_frames]
        self.coordframe.selected = self.coordframe.choices[0]

        self.radius_unit = UnitSelectPluginComponent(
            self, items="radius_unit_items", selected="radius_unit_selected"
        )
        self.radius_unit.choices = ["deg", "rad", "arcmin", "arcsec"]
        self.radius_unit.selected = "deg"

        self.hub.subscribe(self, AddDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, RemoveDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, LinkUpdatedMessage, handler=self.vue_center_on_data)

    @observe("viewer_selected", type="change")
    def vue_viewer_changed(self, _=None):
        # Check mixin object initialized
        if not hasattr(self, "viewer"):
            return

        # Clear all existing subscriptions and resubscribe to selected viewer
        # NOTE: Viewer subscription needed regardless of coord_follow_viewer_pan in order
        #   to detect when coords are centered on viewer, regardless of viewer tracking
        for viewer in self.viewer.viewers:
            if viewer == self.viewer.selected_obj:
                viewer.state.add_callback(
                    "zoom_center_x",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
                viewer.state.add_callback(
                    "zoom_center_y",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
            else:
                # If not subscribed anyways, remove_callback should produce a no-op
                viewer.state.remove_callback(
                    "zoom_center_x",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
                viewer.state.remove_callback(
                    "zoom_center_y",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
        self.vue_center_on_data()

    @observe("coord_follow_viewer_pan", type="change")
    def _toggle_viewer_pan_tracking(self, _=None):
        """Detects when live viewer tracking toggle is clicked and centers on data if necessary"""
        # Center on data if we're enabling the toggle
        if self.coord_follow_viewer_pan:
            self.vue_center_on_data()

    def vue_center_on_data(self, _=None, user_zoom_trigger=False):
        """
        This vue method serves two purposes:
        * UI entrypoint for the manual viewer center button
        * Callback method for user panning (sub'ed to zoom_center_x/zoom_center_y)
        """
        # If plugin is in "Manual" mode, we should never
        # autocenter and potentially wipe the user's data
        if not self.viewer_selected or self.viewer_selected == "Manual":
            return

        # If the user panned but tracking not enabled, don't recenter
        if (user_zoom_trigger) and not self.coord_follow_viewer_pan:
            # Thus, we're no longer centered
            self.viewer_centered = False
            return

        self.center_on_data()

    def center_on_data(self):
        """
        If data is present in the default viewer, center the plugin's coordinates on
        the viewer's center WCS coordinates.
        """
        if not hasattr(self, "viewer"):
            # mixin object not yet initialized
            return

        # gets the current viewer
        viewer = self.viewer.selected_obj

        # nothing happens in the case there is no image in the viewer
        # additionally if the data does not have WCS
        if (
            len(self.app._jdaviz_helper.data_labels) < 1
            or viewer.state.reference_data is None
            or viewer.state.reference_data.coords is None
        ):
            self.source = ""
            return

        # Obtain center point of the current image and convert into sky coordinates
        if self.app._jdaviz_helper.plugins["Orientation"].align_by == "WCS":
            skycoord_center = SkyCoord(
                viewer.state.zoom_center_x, viewer.state.zoom_center_y, unit="deg"
            )
        else:
            skycoord_center = viewer.state.reference_data.coords.pixel_to_world(
                viewer.state.zoom_center_x, viewer.state.zoom_center_y
            )

        # Extract SkyCoord values as strings for plugin display
        ra_deg = skycoord_center.ra.deg
        dec_deg = skycoord_center.dec.deg
        frame = skycoord_center.frame.name.lower()

        # Show center value in plugin
        self.source = f"{ra_deg} {dec_deg}"
        self.coordframe_selected = frame

        self.viewer_centered = True

    @property
    def is_valid(self):
        # these resolvers do not accept any direct, (default_input = None), so can
        # always be considered valid
        return True


def find_matching_resolver(app, inp=None, resolver=None, format=None, target=None, **kwargs):
    formats = format if isinstance(format, (list, tuple)) else [format]
    invalid_resolvers = {}
    valid_resolvers = []
    for resolver_name, Resolver in loader_resolver_registry.members.items():
        if resolver_name == 'file drop':
            # no API input, so let's avoid always returning the confusing
            # message that default_input is undefined
            continue
        if resolver is not None and resolver != resolver_name:
            invalid_resolvers[resolver_name] = f'not {resolver}'
            continue
        try:
            this_resolver = Resolver.from_input(app, inp, format=format, **kwargs)
        except Exception as e:  # nosec
            invalid_resolvers[resolver_name] = f'resolver exception: {e}'
            if resolver_name == 'url' and 'timeout' in str(e):
                raise e
            continue
        try:
            is_valid = this_resolver.is_valid
        except Exception as e:  # nosec
            invalid_resolvers[resolver_name] = f'is_valid exception: {e}'
            is_valid = False
        if not is_valid:
            invalid_resolvers.setdefault(resolver_name, 'not valid')
            continue

        if target is not None:
            try:
                this_resolver.target = target
            except ValueError:
                invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
                continue
        if not len(this_resolver.format.items):
            invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
            continue

        for fmt_item in this_resolver.format.items:
            if (format is not None
                and not any([format in (fmt_item['label'],
                                        fmt_item['parser'],
                                        fmt_item['importer'])
                             for format in formats])):
                invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
                continue
            this_resolver.format.selected = fmt_item['label']
            valid_resolvers.append((this_resolver, resolver_name, fmt_item['label']))

    if len(valid_resolvers) == 0:
        raise ValueError("no valid loaders found for input, tried", invalid_resolvers)
    elif len(valid_resolvers) > 1:
        vrs = [f"resolver={vr[1]} > format={vr[2]}" for vr in valid_resolvers]
        raise ValueError(f"multiple valid loaders found for input: {vrs}")
    else:
        return valid_resolvers[0][0].user_api
