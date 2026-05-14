import warnings
import numpy as np
from astropy.io import fits

from jdaviz.core.loaders.importers.ramp.ramp import RampImporter


def test_ramp_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for RampImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    hdul_valid = fits.HDUList([fits.PrimaryHDU(),
                               fits.ImageHDU(data=np.ones((2, 3, 4, 5)))])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        importer = RampImporter(app=deconfigged_helper._app,
                                resolver=resolver, parser=None,
                                input=hdul_valid)

    # Success: valid 4D HDUList
    # _check_is_valid calls self.output which may warn about missing BUNIT
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        assert importer._check_is_valid() == ''

    # Failure: non-ramp data type
    importer._input = 'not_ramp_data'
    assert importer._check_is_valid() == 'Input is not a supported ramp data type.'

    # Failure: FITS HDUList with NAXIS != 4
    importer._input = fits.HDUList([fits.PrimaryHDU(),
                                    fits.ImageHDU(data=np.ones((3, 3, 3)))])
    assert importer._check_is_valid() == 'FITS HDUList must have NAXIS = 4.'
