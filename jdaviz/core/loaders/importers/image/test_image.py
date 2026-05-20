import numpy as np
import astropy.units as u
from astropy.nddata import NDData, StdDevUncertainty
from astropy.io import fits
from specutils import Spectrum

from jdaviz.core.loaders.importers.image.image import ImageImporter


def test_image_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for ImageImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return ImageImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=input_data)

    # Success: plain 2D numpy array
    importer = _create_importer(input_data=np.ones((10, 10)))
    assert importer._check_is_valid() == ''

    # Failure: Spectrum object (subclasses NDData, which has spectral WCS path,
    # but fails the type check before that)
    spec = Spectrum(flux=np.ones(10) * u.Jy, spectral_axis=np.arange(10) * u.um)
    importer = _create_importer(input_data=np.ones((10, 10)))
    importer._input = spec
    assert importer._check_is_valid() == 'Input is not a supported image data type.'

    # Failure: HDUList with no valid image extensions
    # Can't hotswap with ._input, need to update the extensions attribute (this is
    # the case for several below as well)
    hdul = fits.HDUList([fits.PrimaryHDU(),
                         fits.ImageHDU(data=np.ones((10, 10)))])
    importer = _create_importer(input_data=hdul)
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'

    # Failure: 3D array with no extension choices
    importer = _create_importer(input_data=np.ones((3, 10, 10)))
    importer.input_has_extensions = False
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available for 3D array.'

    # Failure: NDData with spectral GWCS
    s = Spectrum(flux=np.ones((5, 10)) * u.Jy,
                 spectral_axis=np.arange(10) * u.um)
    nddata = NDData(data=np.ones((5, 10)),
                    mask=np.zeros((5, 10), dtype=bool),
                    uncertainty=StdDevUncertainty(np.ones((5, 10)) * 0.1),
                    wcs=s.wcs)
    importer = _create_importer(input_data=nddata)
    assert importer._check_is_valid() == 'Input has spectral WCS coordinates.'
