import logging

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
        wave = self._v1d.state.layers[0].layer.get_component('Wave')
        wavelengths = wave.data[0]
        if index is not None:
            return Spectrum1D(flux=self._v1d.state.layers[0].layer.subsets[index]['FLUX'] * u.Jy,
                              wavelength=wavelengths * u.AA)
        else:
            return [Spectrum1D(flux=layer.layer.subsets[index]['FLUX'] * u.Jy,
                               wavelength=wavelengths * u.AA) for layer in self._v1d.state.layers]
