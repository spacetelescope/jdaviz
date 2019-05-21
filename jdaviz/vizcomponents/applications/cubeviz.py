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
        self.tile_load = v.ListTile(children=[v.ListTileTitle(children=["Load"])])
        self.tile_save = v.ListTile(children=[v.ListTileTitle(children=["Save"])])
        self.tile_load.on_event('click', self._on_change_menu_bar_file)
        self.tile_save.on_event('click', self._on_change_menu_bar_file)
        self.f_items = [self.tile_load, self.tile_save]

        self._menu_bar_file = v.Layout(children=
                                       [v.Menu(offset_y=True,
                                               children=[v.Btn(slot='activator', color='primary',
                                                               children=['File', v.Icon(right=True, children=['arrow_drop_down'])]),
                                                         v.List(children=self.f_items)])
                                        ])

        #
        #  Create Add Viewer Menu
        #
        self.tile_3d_viewer = v.ListTile(
            children=[v.ListTileTitle(children=["3D Viewer"])])
        self.tile_1d_viewer = v.ListTile(
            children=[v.ListTileTitle(children=["1D Viewer"])])
        self.tile_3d_viewer.on_event('click', self._on_change_menu_bar_viewer)
        self.tile_1d_viewer.on_event('click', self._on_change_menu_bar_viewer)
        self.v_items = [self.tile_3d_viewer, self.tile_1d_viewer]


        self._menu_bar_viewer = v.Layout(children=
                                       [v.Menu(offset_y=True,
                                               children=[v.Btn(slot='activator', color='primary',
                                                               children=['Add Viewer', v.Icon(right=True, children=['arrow_drop_down'])]),
                                                         v.List(children=self.v_items)])
                                        ])

        # Add to menu bar
        self._menu_bar = v.Layout(row=True, wrap=True, children=[
                                    v.Flex(xs6=True, class_='px-2', children=[self._menu_bar_file]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._menu_bar_viewer]),
                                ])

        self._menu_bar.box_style = 'success'

        self._v1d = Viewer1D(self._vizapp)
        self._v3d = ViewerND(self._vizapp)

        self._main_box = v.Layout(row=True, wrap=True, children=[
                                    v.Flex(xs12=True, class_='px-2', children=[self._menu_bar]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._v3d.show()]),
                                    v.Flex(xs6=True, class_='px-2', children=[self._v1d.show()]),
                                ])

    def _on_change_menu_bar_file(self, widget, event, data):
        with open("/tmp/bob.log", "a") as f:
            f.write(str(event) + ' ' + str(widget.children[0].children[0]) + '\n')
            f.flush()

    def _on_change_menu_bar_viewer(self, widget, event, data):
        with open("/tmp/bob.log", "a") as f:
            f.write(str(event) + ' ' + widget.children[0].children[0] + '\n')
            f.flush()

        if widget.children[0].children[0] == '3D Viewer':
            # Right now with ipyvuetify the list = list + [new] is the only
            # appending syntax that will update the view
            self._main_box.children = self._main_box.children + \
                                      [v.Flex(xs6=True, classw='px-2', children=[ViewerND(self._vizapp).show()])]

        elif widget.children[0].children[0] == '1D Viewer':
            # Right now with ipyvuetify the list = list + [new] is the only
            # appending syntax that will update the view
            self._main_box.children = self._main_box.children + \
                                      [v.Flex(xs6=True, classw='px-2', children=[Viewer1D(self._vizapp).show()])]

    def show(self):
        return self._main_box

    @property
    def pviewer(self):
        return self._v1d
