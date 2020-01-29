import pytest

import numpy as np

from astropy import units as u
from astropy.units import Quantity
from astropy.units.quantity import allclose

from glue.config import data_translator
from glue.core import Data, DataCollection

from specutils import Spectrum1D


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
        return data.meta['s1d']


def test_translation():
    input_flux   = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
    input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
    spec = Spectrum1D(input_flux, spectral_axis=input_spaxis)

    dc = DataCollection()

    # Translate Spectrum1D -> Data
    dc['spec'] = spec

    assert len(dc) == 1

    assert(isinstance(dc.data[0], Data))
    spectrum = dc.data[0].meta['s1d']
    assert(isinstance(spectrum, Spectrum1D))

    # we could check more of the internals.
    allclose(spectrum.flux, input_flux, atol=1e-5*u.Jy)
    allclose(spectrum.spectral_axis, input_spaxis, atol=1e-5*u.micron)

    # Translate back Data -> Spectrum1D
    spectrum = dc['spec'].get_object()

    assert(isinstance(spectrum, Spectrum1D))

    # we could check more of the internals.
    allclose(spectrum.flux, input_flux, atol=1e-5*u.Jy)
    allclose(spectrum.spectral_axis, input_spaxis, atol=1e-5*u.micron)
