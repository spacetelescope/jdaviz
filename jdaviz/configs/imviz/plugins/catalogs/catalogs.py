from copy import deepcopy

import numpy as np
from astropy import units as u
from astropy.table import QTable, Table as AstropyTable
from astropy.coordinates import SkyCoord
from echo import delay_callback
from traitlets import List, Unicode, Bool, Int, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        FileImportSelectPluginComponent, HasFileImportSelect,
                                        with_spinner)
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import CatalogResultsChangedMessage, CatalogSelectClickEventMessage
from jdaviz.core.marks import CatalogMark
from jdaviz.core.template_mixin import Table, TableMixin, LoadersMixin, DatasetSelect
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import get_top_layer_index

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Catalog Search",
               category="data:analysis")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin,
               TableMixin, LoadersMixin, HasFileImportSelect):
    """
    See the :ref:`Catalog Search Plugin Documentation <imviz-catalogs>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`zoom_to_selected`
    * ``catalog`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Catalog data entry.
    * ``table`` (:class:`~jdaviz.core.template_mixin.Table`):
      Table containing all search results.
    * ``table_selected`` (:class:`~jdaviz.core.template_mixin.Table`):
      Table containing all selected search results.
    """
    template_file = __file__, "catalogs.vue"
    uses_active_status = Bool(True).tag(sync=True)
    catalog_items = List([]).tag(sync=True)
    catalog_selected = Unicode("").tag(sync=True)

    # setting the default table headers and values
    _default_table_values = {
            'Right Ascension (degrees)': np.nan,
            'Declination (degrees)': np.nan,
            'Object ID': np.nan,
            'id': np.nan,
            'x_coord': np.nan,
            'y_coord': np.nan
            }

    headers = ['Right Ascension (degrees)', 'Declination (degrees)',
               'Object ID', 'x_coord', 'y_coord']

    table_selected_widget = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._plugin_description = 'View catalog source entries.'
        self.docs_description = "View table of catalog entries, select inidividual\
                                 sources, and zoom to selected entries."

        self.viewer.add_filter('is_image_viewer')

        cat_options = ['SDSS', 'Gaia']
        if not self.app.state.settings.get('server_is_remote', False):
            cat_options.append('From File...')
        def is_catalog_data(data):
            return len(data.shape) == 1
        self.catalog = FileImportSelectPluginComponent(self,
                                                       items='catalog_items',
                                                       selected='catalog_selected',
                                                       manual_options=cat_options)

        self.catalog = DatasetSelect(self,
                                     items='catalog_items',
                                     selected='catalog_selected',
                                     filters=[is_catalog_data])

        # set the custom file parser for importing catalogs
        self._marker_name = 'catalog_results'

        # initializing the headers in the table that is displayed in the UI
        self.table.headers_avail = self.headers
        self.table.headers_visible = self.headers
        self.table._default_values_by_colname = self._default_table_values
        self.table._selected_rows_changed_callback = self._table_selection_changed
        # note: `item_key` is the name of a column in the
        # table that has unique values for in row
        self.table.item_key = 'id'
        self.table.show_rowselect = True

        def clear_table_callback():
            # gets the current viewer
            viewer = self.viewer.selected_obj

            # resetting values
            self.results_available = False
            self.number_of_results = 0

            if self._marker_name in self.app.data_collection.labels:
                # all markers are removed from the viewer
                viewer.remove_markers(marker_name=self._marker_name)

        self.table._clear_callback = clear_table_callback

        self.table_selected = Table(self, name='table_selected')
        self.table_selected.clear_btn_lbl = 'Clear Selection'
        self.table_selected.show_if_empty = False

        def clear_selected_table_callback():
            self.table.select_none()

        self.table_selected._clear_callback = clear_selected_table_callback
        self.table_selected_widget = 'IPY_MODEL_'+self.table_selected.model_id

        self._update_loader_items()

        self.session.hub.subscribe(self, CatalogSelectClickEventMessage,
                                   self._on_catalog_select_click_event)

        self.observe_traitlets_for_relevancy(traitlets_to_observe=['viewer_items'])

    @property
    def user_api(self):
        # TODO: add 'loaders' once enabled and considered stable (or check dev flag)
        return PluginUserApi(self, expose=('clear_table', 'export_table', 'import_catalog',
                                           'zoom_to_selected', 'select_rows',
                                           'select_all', 'select_none',
                                           'catalog', 'max_sources', 'search',
                                           'table', 'table_selected'))

    @staticmethod
    def _file_parser(path):
        if isinstance(path, AstropyTable):  # includes QTable
            path = deepcopy(path)  # Avoid overwriting original input
            from_file_string = f'API: {path.__class__.__name__} object'
            return '', {from_file_string: path, "_orig_colnames_for_jdaviz_export": path.colnames}

        try:
            table = QTable.read(path)
        except Exception:
            return 'Could not parse file with astropy.table.QTable.read', {}

        if not table.colnames:  # Ensure the file has columns
            return "File contains no columns", {}

        if 'sky_centroid' not in table.colnames:
            return 'Table does not contain required sky_centroid column', {}

        table.meta["_orig_colnames_for_jdaviz_export"] = table.colnames
        return '', {path: table, "_orig_colnames_for_jdaviz_export": table.colnames}

    def _on_catalog_select_click_event(self, msg):
        xs, ys = self.table._qtable['x_coord'], self.table._qtable['y_coord']
        # nearest point
        distsq = (xs - msg.x)**2 + (ys - msg.y)**2
        ind = np.argmin(distsq)
        item = self.table.items[ind]
        if item in self.table.selected_rows:
            self.table.selected_rows = [sr for sr in self.table.selected_rows if sr != item]
        else:
            self.table.selected_rows += [item]
        self._table_selection_changed()


    def _get_mark(self, viewer):
        matches = [mark for mark in viewer.figure.marks if isinstance(mark, CatalogMark)]
        if len(matches):
            return matches[0]
        mark = CatalogMark(viewer)
        viewer.figure.marks = viewer.figure.marks + [mark]
        return mark

    @property
    def marks(self):
        return {viewer_id: self._get_mark(viewer)
                for viewer_id, viewer in self.app._viewer_store.items()
                if hasattr(viewer, 'figure')}

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if self.disabled_msg:
            return

        for mark in self.marks.values():
            mark.visible = self.is_active

    def _table_selection_changed(self, msg={}):
        selected_rows = self.table.selected_rows

        self.table_selected._clear_table()
        for selected_row in selected_rows:
            self.table_selected.add_item(selected_row)

        if (self.table_selected._qtable and
                "_orig_colnames_for_jdaviz_export" in self.catalog._cached_obj):
            self.table_selected._qtable.meta["_orig_colnames_for_jdaviz_export"] = self.catalog._cached_obj["_orig_colnames_for_jdaviz_export"]  # noqa: E501

        x = [float(coord['x_coord']) for coord in selected_rows]
        y = [float(coord['y_coord']) for coord in selected_rows]
        self._get_mark(self.viewer.selected_obj).update_xy(getattr(x, 'value', x),
                                                           getattr(y, 'value', y))

    def vue_zoom_in(self, *args, **kwargs):
        self.zoom_to_selected()

    def zoom_to_selected(self, padding=0.02, return_bounding_box=False):
        """
        Zoom on the default viewer to a region containing the currently selected
        points in the catalog.

        Parameters
        ----------
        padding : float, optional
            A fractional value representing the padding around the bounding box
            of the selected points. It is applied as a proportion of the largest
            dimension of the current extent of loaded data. Defaults to 0.02.
        return_bounding_box : bool, optional
            If True, returns the bounding box of the zoomed region as
            ((x_min, x_max), (y_min, y_max)). Defaults to False.

        Returns
        -------
        bb : list of float or None
            If there are activley selected rows, and ``return_bounding_box`` is
            True, returns a list containing the bounding
            box coordinates: ``[x_min, x_max, y_min, y_max]``.
            Otherwise, returns `None`.

        """
        viewer = self.viewer.selected_obj  # gets the current viewer

        selected_rows = self.table.selected_rows
        if not selected_rows:  # Check if no rows are selected
            return

        if padding <= 0 or padding > 1:
            raise ValueError("padding must be between 0 (exclusive) and 1 (inclusive).")

        i_top = get_top_layer_index(viewer)
        image = viewer.layers[i_top].layer
        x_min = 99999
        x_max = -99999
        y_min = 99999
        y_max = -99999
        for coord in selected_rows:  # list of dict
            cur_x, cur_y = viewer._get_real_xy(
                image, float(coord['x_coord']), float(coord['y_coord']))[:2]
            if cur_x < x_min:
                x_min = cur_x
            if cur_x > x_max:
                x_max = cur_x
            if cur_y < y_min:
                y_min = cur_y
            if cur_y > y_max:
                y_max = cur_y

        if x_min == x_max and y_min == y_max:  # Only one selected
            pass
        elif x_min >= x_max or y_min >= y_max:
            raise ValueError(
                f"Zoom failed: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")

        pix_pad = padding * max(x_max, y_max)
        x_min -= pix_pad
        x_max += pix_pad
        y_min -= pix_pad
        y_max += pix_pad
        new_y_min = viewer._get_real_xy(image, x_min, y_min, reverse=True)[1]
        new_y_max = viewer._get_real_xy(image, x_max, y_max, reverse=True)[1]

        # First, we center using image's coordinates.
        viewer.center_on((0.5 * (x_min + x_max), 0.5 * (y_min + y_max)))

        # Then, we zoom using reference data's coordinates. This is important when WCS linked.
        # We cannot use viewer.zoom_level because it is wonky when WCS linked.
        # Given most displays are wider in X, we make sure Y coordinates all fit first
        # and X will naturally all fit within after aspect ratio is taken into account.
        with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            viewer.state.y_min = new_y_min
            viewer.state.y_max = new_y_max
        viewer.state._adjust_limits_aspect()

        if return_bounding_box:
            return [viewer.state.x_min, viewer.state.x_max, viewer.state.y_min, viewer.state.y_max]
