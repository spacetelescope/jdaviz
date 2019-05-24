import logging

from ipywidgets import Box
from .viewer import Viewer

logging.basicConfig(filename='/tmp/vizapp.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger('viewernd')


class ViewerND(Viewer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._v3d = self._glue_app.imshow(data=self._glue_app.data_collection[0])

    def show(self):
        return Box([self._v3d.layout])
