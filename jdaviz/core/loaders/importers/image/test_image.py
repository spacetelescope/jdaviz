import numpy as np
import astropy.units as u
from astropy.nddata import NDData, StdDevUncertainty
from astropy.io import fits
from specutils import Spectrum

from jdaviz.core.loaders.importers.image.image import ImageImporter


def test_image_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in ImageImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return ImageImporter(app=deconfigged_helper._app,
                             resolver=resolver, parser=None,
                             input=input_data)

    # Init with valid 2D array, swap to Spectrum (which subclasses NDData)
    spec = Spectrum(flux=np.ones(10) * u.Jy, spectral_axis=np.arange(10) * u.um)
    importer = _create_importer(input_data=np.ones((10, 10)))
    importer._input = spec
    assert importer._check_is_valid() == 'Input is not a supported image data type.'

    # Init with valid HDUList, then clear extension choices
    hdul = fits.HDUList([fits.PrimaryHDU(),
                         fits.ImageHDU(data=np.ones((10, 10)))])
    importer = _create_importer(input_data=hdul)
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available.'

    # Init with valid 3D array, clear extensions, set input_has_extensions=False
    # to bypass the generic check and reach the 3D-specific one
    importer = _create_importer(input_data=np.ones((3, 10, 10)))
    importer.input_has_extensions = False
    importer.extension.items = []
    assert importer._check_is_valid() == 'No extensions available for 3D array.'

    # Create NDData with spectral GWCS (all 3 components to satisfy `all()` check)
    s = Spectrum(flux=np.ones((5, 10)) * u.Jy,
                 spectral_axis=np.arange(10) * u.um)
    nddata = NDData(data=np.ones((5, 10)),
                    mask=np.zeros((5, 10), dtype=bool),
                    uncertainty=StdDevUncertainty(np.ones((5, 10)) * 0.1),
                    wcs=s.wcs)
    importer = _create_importer(input_data=nddata)
    assert importer._check_is_valid() == 'Input has spectral WCS coordinates.'
