from __future__ import absolute_import, division, print_function

from ipywidgets import widgets

from ..viewer.image_viewer import ImageVizWidget


class ImageViz:

    data = None

    def __init__(self, vizapp, data=None):

        self._vizapp = vizapp
        self.data = data

        self._image_widget = ImageVizWidget(session=self._vizapp.glue_app.session)

        self._main_box = widgets.Box([widgets.VBox([self._image_widget])])

        if data:
            self.add_data(data)

    def add_data(self, data):
        self.data = data
        self._image_widget.add_data(data)

    def show(self):
        return self._main_box
