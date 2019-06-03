from __future__ import absolute_import, division, print_function
import numpy as np

from ipywidgets import widgets

from glue.core.data import Component, Data
from glue.core.component import CategoricalComponent
from glue.config import data_factory, qglue_parser
from glue.core.data_factories.astropy_table import is_readable_by_astropy, astropy_table_read

from ..viewer.mos_table_viewer import MOSVizTable
from ..viewer.mos_viewer import MOSVizWidget


@data_factory(label="MOSViz Table (ascii.ecsv)",
              identifier=is_readable_by_astropy,
              priority=3)
def mosviz_tabular_data(*args, **kwargs):
    """
     Build a data set from a table. We restrict ourselves to tables
     with 1D columns.

     All arguments are passed to
         astropy.table.Table.read(...).
     """

    result = Data()

    table = astropy_table_read(*args, **kwargs)

    result.meta = table.meta

    # Loop through columns and make component list
    for column_name in table.columns:
        c = table[column_name]
        u = c.unit if hasattr(c, 'unit') else c.units

        if table.masked:
            # fill array for now
            try:
                c = c.filled(fill_value=np.nan)
            except (ValueError, TypeError):  # assigning nan to integer dtype
                c = c.filled(fill_value=-1)

        dtype = c.dtype.type
        if dtype is np.string_ or dtype is np.str_:
            nc = CategoricalComponent(c, units=u)
        else:
            nc = Component.autotyped(c, units=u)
        result.add_component(nc, column_name)

    return result


class ImageViz:

    data = None

    def __init__(self, vizapp, data=None, filename=None):

        print ('@@@@@@     line: 61  -   New class!')

        self._vizapp = vizapp

        self.mostable = None
        self.mostable_dir = None
        self.data = data
        self.html = None
        self.current_cutout = None

        #  Create File Menu
        self._menu_bar_file = widgets.Dropdown(
            options=['File', 'Load', 'Save'],
            value='File',
            description='',
            layout=widgets.Layout(width='10em'),
        )

        self._menu_bar_file.observe(self._on_change_menu_bar_file)
        self._menu_bar = widgets.HBox([self._menu_bar_file])

        #  Create Navigation Bar
        self._current_slit = widgets.Dropdown(
            options=[],
            description='Slit',
            layout=widgets.Layout(width='20em'),
        )
        self._current_slit.observe(self._on_change_current_slit)

        self._next_button = widgets.Button(description="Next")
        self._next_button.on_click(self._on_next)

        self._back_button = widgets.Button(description="Back")
        self._back_button.on_click(self._on_back)

        self._nav_bar = widgets.HBox([self._current_slit, self._back_button, self._next_button])

        # the table viewer must be built with the data already in. This allows the
        # column headers to be properly set (it's an ipysheet API constraint). For
        # now, the code only works when data is not None.
        self._table = MOSVizTable(session=self._vizapp.glue_app.session, data=data)
        self._mos_widget = MOSVizWidget(session=self._vizapp.glue_app.session)

        self._viewer_box = widgets.VBox([self._mos_widget, self._table.show()])

        self._main_box = widgets.Box([widgets.VBox([self._nav_bar, self._table.show(), self._mos_widget])])

        if data:
            self.add_data(data)

        # not sure on how this works. Probably depends on what we
        # want the user interface to look at the notebook level.
        # It's not being exercised yet.
        if filename:
            self._vizapp.glue_app.load_data(filename)

    def _populate_dropdown(self):
        if self.data is None:
            self._current_slit.options = []
        else:
            options = list([i[0] for i in self._mos_widget._rows])
            self._current_slit.options = options
            if len(options) > 0:
                self._current_slit.value = options[0]
        self._on_change_current_slit()

    def add_data(self, data):
        self.data = data
        # update everything but the table viewer. The table viewer must
        # be populated at the time it's built, so that the table column
        # headers can be set (it's an ipysheet API constraint).
        self._mos_widget.add_data(data)
        self._populate_dropdown()
        if len(self._current_slit.options) > 0:
            self.current_slit_index = 0

    @property
    def current_slit_index(self):
        if self._mos_widget:
            return self._mos_widget.current_index

    @current_slit_index.setter
    def current_slit_index(self, value):
        if self._mos_widget:
            self._mos_widget.current_index = value
            if self._mos_widget.current_index is None:
                return
            self._current_slit.index = self._mos_widget.current_index
            self._table._select_row(idx=self._mos_widget.current_index)

    def _on_change_current_slit(self, *args):
        target = self._current_slit.value
        if target is None:
            return
        idx = list(self.data['id']).index(target)
        self.current_slit_index = idx

    def _on_change_menu_bar_file(self):
        pass

    def _on_next(self, *args):
        self.current_slit_index = self._mos_widget.current_index + 1

    def _on_back(self, *args):
        self.current_slit_index = self._mos_widget.current_index - 1

    def show(self):
        return self._main_box
