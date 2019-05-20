from ipywidgets import widgets
import ipyvuetify as v

from ..viewer.viewernd import ViewerND
from ..viewer.viewer1d import Viewer1D


class CubeViz:

    def __init__(self, filename, vizapp):

        self._vizapp = vizapp

        self._vizapp.glue_app.load_data(filename)

        #
        #  Create File Menu
        #
        self._menu_bar_file = widgets.Dropdown(
            options=['File', 'Load', 'Save'],
            value='File',
            description='',
            layout=widgets.Layout(width='10em'),
        )
        #
        # items = [v.ListTile(children=[v.ListTileTitle(children=["Load"])]),
        #          v.ListTile(children=[v.ListTileTitle(children=["Save"])])]
        #
        # self._menu_bar_file = v.Layout(children=[v.Menu(offset_y=True,
        #               children=[v.Btn(slot='activator',
        #                                            color='primary',
        #                                            children=['File',
        #                                                      v.Icon(right=True,
        #                                                             children=['arrow_drop_down'])]),
        #                                      v.List(children=items)])
        #                                          ])

        self._menu_bar_file.observe(self._on_change_menu_bar_file)

        #
        #  Create Add Viewer Menu
        #
        self._menu_bar_viewer = widgets.Dropdown(
            options=['Add Viewer', '3D Viewer', '1D Viewer'],
            value='Add Viewer',
            description='',
            layout=widgets.Layout(width='10em'),
        )
        self._menu_bar_viewer.observe(self._on_change_menu_bar_viewer)

        # Add to menu bar
        self._menu_bar = v.Layout(children=[self._menu_bar_file, self._menu_bar_viewer])
        self._menu_bar.box_style = 'success'

        self._v1d = Viewer1D(self._vizapp)
        self._v3d = ViewerND(self._vizapp)

        # this is the line where we would put ipyvutify
        self._main_box = v.Layout(children=[widgets.VBox([self._menu_bar, widgets.HBox([self._v3d.show(), self._v1d.show()])])])
        #self._main_box = v.Layout(children=[self._menu_bar, self._v3d.show(), self._v1d.show()])

    def _on_change_menu_bar_file(self, change):
        print(change)

    def _on_change_menu_bar_viewer(self, change):
        print(change)

    def show(self):
        return self._main_box

    @property
    def pviewer(self):
        return self._v1d
