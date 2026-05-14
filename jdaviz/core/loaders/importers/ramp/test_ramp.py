import warnings
import numpy as np
from astropy.io import fits

from jdaviz.core.loaders.importers.ramp.ramp import RampImporter


def test_ramp_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in RampImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Create with valid 4D HDUList (RampImporter init triggers a BUNIT warning)
    hdul_valid = fits.HDUList([fits.PrimaryHDU(),
                               fits.ImageHDU(data=np.ones((2, 3, 4, 5)))])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        importer = RampImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=hdul_valid)

    # Non-ramp data type
    importer._input = 'not_ramp_data'
    assert importer._check_is_valid() == 'Input is not a supported ramp data type.'

    # FITS HDUList with NAXIS != 4
    importer._input = fits.HDUList([fits.PrimaryHDU(),
                                    fits.ImageHDU(data=np.ones((3, 3, 3)))])
    assert importer._check_is_valid() == 'FITS HDUList must have NAXIS = 4.'
