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

    def __init__(self, vizapp, data=None, filename=None):

        self._vizapp = vizapp

        self.mostable = None
        self.mostable_dir = None
        self.data = data
        self.html = None
        self.current_cutout = None

        # Create control bar with drop down bar (OverflowBtn), back button, and next button

        self._back_button = v.Btn(children=["Back"], color="info")
        self._next_button = v.Btn(children=["Next"], color="info")

        self._back_button.on_event("click", self._on_back)
        self._next_button.on_event("click", self._on_next)

        self._control_bar = v.Layout(row=True, wrap=True, children=[self._back_button, self._next_button])

        self._current_slit = v.OverflowBtn(label="Slit", v_model=None,  items=[], width=10)
        self._current_slit.observe(self._on_change_current_slit, names=['v_model'])

        # Add to menu bar
        self._menu_bar = v.Layout(row=True, wrap=True, children=[
                                    v.Flex(xs6=True, class_='px-2', children=[self._current_slit]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._control_bar])

        ])

        # Create table and mos_widget

        # the table viewer must be built with the data already in. This allows the
        # column headers to be properly set (it's an ipysheet API constraint). For
        # now, the code only works when data is not None.
        self._table = MOSVizTable(session=self._vizapp.glue_app.session, data=data)
        self._mos_widget = MOSVizWidget(session=self._vizapp.glue_app.session)

        # Combine into main

        self._main_box = v.Layout(row=True, wrap=True, children=[
            self._menu_bar, self._table.show(), self._mos_widget
        ])

        if data:
            self.add_data(data)

        # not sure on how this works. Probably depends on what we
        # want the user interface to look at the notebook level.
        # It's not being exercised yet.
        if filename:
            self._vizapp.glue_app.load_data(filename)

    def _populate_dropdown(self):
        """
        Vuetify version of the populate dropdown function
        """
        if self.data is None:
            self._current_slit.items = []
        else:
            self._current_slit.items = list([i[0] for i in self._mos_widget._rows])


    def add_data(self, data):
        self.data = data
        # update everything but the table viewer. The table viewer must
        # be populated at the time it's built, so that the table column
        # headers can be set (it's an ipysheet API constraint).
        self._mos_widget.add_data(data)
        self._populate_dropdown()
        if len(self._current_slit.items) > 0:
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
            # self._current_slit.index = self._mos_widget.current_index
            if len(self._current_slit.items) > 0:
                self._current_slit.v_model = self._current_slit.items[self._mos_widget.current_index]
            self._table._select_row(idx=self._mos_widget.current_index)

    def _on_change_current_slit(self, v):
        idx = list(self.data['id']).index(v.new)
        self.current_slit_index = idx

    def _on_change_menu_bar_file(self):
        pass

    def _on_next(self, *args):
        self.current_slit_index = self._mos_widget.current_index + 1

    def _on_back(self, *args):
        self.current_slit_index = self._mos_widget.current_index - 1

    def show(self):
        return self._main_box
