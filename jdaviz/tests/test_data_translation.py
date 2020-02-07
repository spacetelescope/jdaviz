import numpy as np

from astropy import units as u
from astropy.io import fits
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
        try:
            result = data.meta['s1d']
        except KeyError:
            result = data.label
        return result


def test_translation():
    input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
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


def test_translation_real_data():

    # The description on issue JDAT-136 reads:
    #
    # "Doing the operation over a spectrum object that's been read
    # into glue-jupyter by converting back into a spectrum, doing
    # the specutils, and then putting it back into the data collection."
    #
    # Taking it literally, we should expect that something like this
    # would be possible:
    #
    # >>> data = Data('https://dr14.sdss.org/optical/spectrum/view/...
    # >>> spec = data.get_object(cls=Spectrum1D)
    # >>> assert(isinstance(spec, Spectrum1D))
    #
    # That is not possible because the internal reader in Data doesn't
    # have access to a data translator.
    #
    # Instead, we repeat here more or less the same test as above.

    f = fits.open('https://dr14.sdss.org/optical/spectrum/view/data/format=fits/spec=lite?plateid=1323&mjd=52797&fiberid=12')
    specdata = f[1].data
    f.close()

    flux_unit = u.Unit('erg cm-2 s-1 AA-1')
    spaxis_unit = u.Unit('Angstrom')

    lamb = 10 ** specdata['loglam'] * spaxis_unit
    flux = specdata['flux'] * 10 ** -17 * flux_unit
    spec = Spectrum1D(spectral_axis=lamb, flux=flux)

    data = Data(spec)

    spectrum = data.get_object(cls=Spectrum1D)
    assert(isinstance(spectrum, Spectrum1D))

    allclose(spectrum.flux, flux, atol=1e-5*flux_unit)
    allclose(spectrum.spectral_axis, lamb, atol=1e-5*spaxis_unit)
