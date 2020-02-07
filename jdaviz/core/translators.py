import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.units import Quantity
from astropy.units.quantity import allclose
from glue.config import data_translator
from glue.core import Data, DataCollection

from specutils import Spectrum1D

__all__ = ['Spectrum1DHandler']


@data_translator(Spectrum1D)
class Spectrum1DHandler:
    def to_data(self, obj):
        data = Data()
        data['spectral_axis'] = obj.spectral_axis
        data['flux'] = obj.data
        data.get_component('flux').units = str(obj.flux.unit)
        data.meta['s1d'] = obj
        return data

    def to_object(self, data):
        try:
            result = data.meta['s1d']
        except KeyError:
            result = data.label
        return result
