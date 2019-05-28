import logging

import numpy as np
from ipywidgets import Box
from astropy import units as u
from glue.core.subset import RangeSubsetState
from specutils import Spectrum1D, SpectralRegion

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
        self._v1d = self._glue_app.profile1d(data=self._glue_app.data_collection[0], show=False)

    def show(self):
        return Box([self._v1d.layout])

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
        # this should be replaced by something glue-native... it really only works for the specific cubes in testing
        dc = self._vizapp.glue_app.data_collection
        flux_unit = u.Unit(dc[0].meta['BUNIT'].replace('/spaxel', '').replace('Ang', 'angstrom'))
        wave_unit = u.Unit(dc[0].meta['CUNIT3'])

        x, y = self._v1d.state.layers[0].profile
        return Spectrum1D(spectral_axis=x*wave_unit, flux=y*flux_unit)
