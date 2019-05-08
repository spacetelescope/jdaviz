import logging

from .simple_bqplot_image import simple_imshow
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

        self._v3d = simple_imshow(self._glue_app, data=self._glue_app.data_collection[0])

    def show(self):
        return self._v3d.main_widget
