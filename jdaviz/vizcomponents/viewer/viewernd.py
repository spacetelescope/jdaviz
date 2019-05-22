import inspect
import logging

import numpy as np
from ipywidgets import Box

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

        self._3d_processing = {}
        self.add_3d_processing("Median Collapse over Wavelenths", np.nanmedian, 'a', (('axis', 0),))
        self.add_3d_processing("Mean Collapse over Wavelenths", np.nanmean, 'a', (('axis', 0),))
        self.add_3d_processing("Median Collapse over Space", np.nanmedian, 'a', (('axis', (1,2)),))
        self.add_3d_processing("Mean Collapse over Space", np.nanmean, 'a', (('axis', (1,2)),))

    def add_3d_processing(self, name, func, data_parameter, parameters):
        """

        :param name: str name to display
        :param func: method  method to run
        :param parameters: tuple - list of parameters
        :return: none
        """
        logger.debug('parameters is {}'.format(parameters))

        if not isinstance(name, str):
            raise TypeError('add_3d_processing: name, {}, must be a string')

        if not inspect.isfunction(func):
            raise TypeError('add_3d_processing: func must be a method')

        if not isinstance(data_parameter, str):
            raise TypeError('add_3d_processing: data_parameter, {}, must be a string')

        if not isinstance(parameters, (list, tuple)):
            raise TypeError('add_3d_processing: parameters must be a list')

        if parameters:
            if any([not isinstance(x, tuple) or not len(x) in [0, 2] for x in parameters]):
                raise TypeError('add_3d_processing: each parameter must be a parameter name and default value')

        if name in self._3d_processing:
            logger.warning('Replacing {} in the 3D processing'.format(name))

        self._3d_processing[name] = {
            'name': name,
            'method': func,
            'data_parameter': data_parameter,
            'parameters': parameters
        }

    def get_3d_processing(self, name=None):
        """
        Get the list of types of processing that can be done on a 3D dataset

        :return: list - list of keys to the types of processing
        """
        # TODO: Fix the above description

        if name is not None:
            return self._3d_processing[name]
        else:
            return list(self._3d_processing.keys())

    def show(self):
        return Box([self._v3d.main_widget])

