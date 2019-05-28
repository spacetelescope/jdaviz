import logging

import numpy as np
from astropy import units as u
from specutils import Spectrum1D

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
        self._v3d = self._glue_app.imshow(data=self._glue_app.data_collection[0], show=False)

    def show(self):
        return Box([self._v3d.layout])

    def getSpectrum1D(self, index=-1):
        # this should be replaced by something glue-native... it really only works for the specific cubes in testing
        dc = self._vizapp.glue_app.data_collection
        flux_unit = u.Unit(dc[0].meta['BUNIT'].replace('/spaxel', '').replace('Ang', 'angstrom'))
        wave_unit = dc[0].meta['CUNIT3']

        wave = self._v3d.state.layers[0].layer.get_component('Wave')
        wavelengths = wave.data[:, 0, 0]

        flux = self._v3d.state.layers[index].layer['FLUX']
        if len(flux.shape) == 3:
            # spectrum1D should be [M1,M2,...], N where N is the wavelength axis, but the cube is (N, M1, M2)
            reflux = np.moveaxis(flux, 0, -1)
        elif len(flux.shape) == 1:
            # subsets are flattened.  We assume the leading axis is the wavelength axis for consistency with above
            reflux = flux.reshape(wavelengths.shape[0], flux.shape[0]//wavelengths.shape[0])
            # but now transpose to get [M, N]
            reflux = reflux.T
        else:
            raise ValueError('unexpected shape of data cube')

        return Spectrum1D(flux=reflux * flux_unit,
                          spectral_axis=wavelengths * wave_unit)
