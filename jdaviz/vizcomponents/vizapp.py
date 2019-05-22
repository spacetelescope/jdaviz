import logging

import glue_jupyter as gj

from .viewer import viewer1d, viewernd

logging.basicConfig(filename='/tmp/vizapp.log',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)
logger = logging.getLogger('vizapp')


class VizApp:

    def __init__(self):

        self._glue_app = gj.jglue()
        self._history = []


    @property
    def glue_app(self):
        return self._glue_app

    def viewer1D(self):
        return viewer1d.Viewer1D(self)

    def viewerND(self):
        return viewernd.ViewerND(self)

    # ---------------------------------------------------------------
    #
    #  data
    #
    # ---------------------------------------------------------------

    def add_data(self, filename):
        """
        Add data to the vizapp object. This can be 1D, 2D or 3D.

        :param filename: Filename of the dataset.
        :return:
        """
        # TODO: Refactor this
        self._glue_app.add_data(filename)


    def get_data(self, name):
        """
        Get the data from one of the data containers.

        :param name: str or int  key for lookup
        :return:
        """

        if isinstance(name, int):
            key = list(self._3d_data.keys())[0]

            if not key:
                return None

            return self._3d_data[key]
        elif isinstance(name, str):
            if name in self._3d_data:
                return self._3d_data[name]
            elif name in self._2d_data:
             return self._2d_data[name]
            elif name in self._1d_data:
                return self._1d_data[name]
        else:
            raise('get_data takes an int or string.')
