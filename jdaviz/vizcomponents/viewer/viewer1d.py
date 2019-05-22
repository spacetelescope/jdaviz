import inspect
import logging

import numpy as np
import scipy.signal
from astropy import units as u
from glue.core.subset import RangeSubsetState
from ipywidgets import Box
from specutils import Spectrum1D, SpectralRegion

from .simple_bqplot_profile import simple_profile
from .viewer import Viewer

logging.basicConfig(filename='/tmp/vizapp.log',
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger('viewer1d')


class Viewer1D(Viewer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._v1d = simple_profile(self._glue_app, data=self._glue_app.data_collection[0])

        self._1d_processing = {}
        self.add_1d_processing("Median Smoothing", scipy.signal.medfilt, 'volume', (('kernel_size', 3),))
        self.add_1d_processing("Hanning Smoothing", np.convolve, 'a', (('mode', 'valid'), ('w', np.hanning(3))))
        self.add_1d_processing("Hamming Smoothing", np.convolve, 'a', (('mode', 'valid'), ('w', np.hamming(3))))
        self.add_1d_processing("Bartlett Smoothing", np.convolve, 'a', (('mode', 'valid'), ('w', np.bartlett(3))))
        self.add_1d_processing("Blackman Smoothing", np.convolve, 'a', (('mode', 'valid'), ('w', np.blackman(3))))

    def show(self):
        return Box([self._v1d.main_widget])

    def getRegion(self, index=None):

        if index is not None:
            subset = self._v1d.state.layers[index].layer
            if hasattr(subset, 'subset_state') and isinstance(subset.subset_state, RangeSubsetState):
                return SpectralRegion(subset.subset_state.lo*u.AA, subset.subset_state.hi*u.AA)
            else:
                return None
        else:
            return [SpectralRegion(l.layer.subset_state.lo*u.AA, l.layer.subset_state.hi*u.AA) for l in
                    self._v1d.state.layers if
                    hasattr(l.layer, 'subset_state') and isinstance(l.layer.subset_state, RangeSubsetState)]

    def getSpectrum1D(self, index=0):
        wave = self._v1d.state.layers[0].layer.get_component('Wave')
        wavelengths = wave.data[0]
        if index is not None:
            return Spectrum1D(flux=self._v1d.state.layers[0].layer.subsets[index]['FLUX'] * u.Jy,
                              wavelength=wavelengths * u.AA)
        else:
            return [Spectrum1D(flux=layer.layer.subsets[index]['FLUX'] * u.Jy,
                               wavelength=wavelengths * u.AA) for layer in self._v1d.state.layers]

    def add_1d_processing(self, name, func, data_parameter, parameters):
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
            if any([not isinstance(x, tuple) or not len(x) in [0,2] for x in parameters]):
                raise TypeError('add_3d_processing: each parameter must be a parameter name and default value')

        if name in self._1d_processing:
            logger.warning('Replacing {} in the 3D processing'.format(name))

        self._1d_processing[name] = {
            'name': name,
            'method': func,
            'data_parameter': data_parameter,
            'parameters': parameters
        }


    def get_1d_processing(self, name=None):
        """
        Get the list of types of processing that can be done on a 3D dataset

        :return: list - list of keys to the types of processing
        """
        # TODO: Fix the above description

        if name is not None:
            return self._1d_processing[name]
        else:
            return list(self._1d_processing.keys())

