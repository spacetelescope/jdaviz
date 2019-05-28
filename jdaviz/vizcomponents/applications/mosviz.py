from __future__ import absolute_import, division, print_function
import numpy as np

from ipywidgets import widgets

import ipyvuetify as v

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


class MOSViz:

    data = None

    def __init__(self, vizapp, filename=None):

        self._vizapp = vizapp

        self.mostable = None
        self.mostable_dir = None
        self.data = None
        self.html = None
        self.current_cutout = None

        #  Create File Menu
        # self._menu_bar_file = widgets.Dropdown(
        #     options=['File', 'Load', 'Save'],
        #     value='File',
        #     description='',
        #     layout=widgets.Layout(width='10em'),
        # )
        self.tile_load = v.ListTile(children=[v.ListTileTitle(children=["Load"])])
        self.tile_save = v.ListTile(children=[v.ListTileTitle(children=["Save"])])
        self.f_items = [self.tile_load, self.tile_save]

        self._menu_bar_file = v.Layout(children=
                                       [v.Menu(offset_y=True,
                                               children=[v.Btn(slot='activator', color='primary',
                                                               children=['File', v.Icon(right=True,
                                                                                        children=['arrow_drop_down'])]),
                                                         v.List(children=self.f_items)])
                                        ])

        self._back_button_vuetify = v.Btn(children=["Back"], color="info")
        self._next_button_vuetify = v.Btn(children=["Next"], color="info")

        self._current_slit_vuetify = v.OverflowBtn(label="Slit", items=[], width='20em')

        # self._current_slit_vuetify.on_event

        # Add to menu bar
        self._menu_bar = v.Layout(row=True, wrap=True, children=[
                                    v.Flex(xs6=True, class_='px-2', children=[self._back_button_vuetify]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._next_button_vuetify]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._current_slit_vuetify])

        ])


        #  Create Navigation Bar
        self._current_slit = widgets.Dropdown(
            options=[],
            description='Slit',
            layout=widgets.Layout(width='20em'),
        )
        self._current_slit.observe(self._on_change_current_slit)

        self._next_button = widgets.Button(description="Next")
        self._next_button.on_click(self._on_next)
        self._next_button_vuetify.on_event("click", self._on_next)


        self._back_button = widgets.Button(description="Back")
        self._back_button.on_click(self._on_back)
        self._back_button_vuetify.on_event("click", self._on_back)


        self._nav_bar = widgets.HBox([self._current_slit, self._back_button, self._next_button])

        self._table = MOSVizTable(session=self._vizapp.glue_app.session)
        self._mos_widget = MOSVizWidget(session=self._vizapp.glue_app.session)

        self._viewer_box = widgets.VBox([self._mos_widget, self._table.show()])

        self._main_box = widgets.Box([widgets.VBox([self._menu_bar, self._nav_bar, self._table.show(), self._mos_widget])])

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

    def _populate_dropdown_vuetify(self):
        if self.data is None:
            self._current_slit_vuetify.items = []
        else:
            options = list([i[0] for i in self._mos_widget._rows])
            self._current_slit_vuetify.items = options
            if len(options) > 0:
                self._current_slit_vuetify.items = options[0]
        # self._on_change_current_slit()

    def add_data(self, data):
        self.data = data
        self._table.add_data(data)
        self._mos_widget.add_data(data)
        self._populate_dropdown()
        # self._populate_dropdown_vuetify()
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

    def _on_change_current_slit_vuetify(self, *args):
        target = self._current_slit_vuetify.value
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
