import astropy.units as u
import numpy as np
import pytest
from astropy.io import fits

from jdaviz.core.loaders.importers.spectrum1d.spectrum1d import SpectrumImporter


@pytest.mark.parametrize('extname,n_flux_cols', [('EXTRACT1D', 1), ('EXTRACT5PIX1D', 2)])
def test_spectrum1d_table_hdu_nonstandard_unit(deconfigged_helper, extname, n_flux_cols):
    """
    Regression test for JWST/JADES x1d-style tables whose TUNIT values use 'AA'
    for Angstrom, which is rejected by astropy's strict FITS unit parser and
    left as an UnrecognizedUnit. These should still be parsed as valid spectra
    (single 'EXTRACT1D' extension, or multiple FLUX/FLUX_ERR pairs as in
    'EXTRACT5PIX1D').
    """
    n = 10
    cols = [fits.Column(name='WAVELENGTH', format='D', unit='um',
                        array=np.linspace(1.0, 2.0, n))]
    for i in range(n_flux_cols):
        suffix = '' if i == 0 else '_NOD2'
        cols.append(fits.Column(name=f'FLUX{suffix}', format='D',
                                unit='erg s-1 cm-2 AA-1',
                                array=np.linspace(10, 20, n)))
        cols.append(fits.Column(name=f'FLUX_ERR{suffix}', format='D',
                                unit='erg s-1 cm-2 AA-1',
                                array=np.full(n, 0.1)))
    hdu = fits.BinTableHDU.from_columns(cols, name=extname)
    hdul = fits.HDUList([fits.PrimaryHDU(), hdu])

    resolver = deconfigged_helper.loaders['object']._obj
    importer = SpectrumImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=hdul)

    spec = importer.spectra[0]
    assert spec.flux.unit == u.Unit('erg s-1 cm-2 AA-1')
    np.testing.assert_allclose(spec.spectral_axis.to_value(u.um), hdu.data['WAVELENGTH'])
    np.testing.assert_allclose(spec.flux.value, hdu.data['FLUX'])
