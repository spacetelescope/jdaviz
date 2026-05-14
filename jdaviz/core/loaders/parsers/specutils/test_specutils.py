import numpy as np
import astropy.units as u
from astropy.table import QTable

from jdaviz.core.loaders.parsers.specutils.specutils import (SpecutilsSpectrumArrayParser,
                                                             SpecutilsSpectrumListParser)


def test_specutils_parser_is_valid(deconfigged_helper, tmp_path):
    """Test all string-returning scenarios in specutils parser _check_is_valid methods."""
    # SpecutilsSpectrumArrayParser: non-array and wrong dimensions
    for inp in ('not_an_array', np.ones((2, 2, 2, 2))):
        parser = SpecutilsSpectrumArrayParser(deconfigged_helper._app, inp)
        assert parser._check_is_valid() == ('Input must be a numpy array with '
                                            '1, 2, or 3 dimensions.')

    # SpecutilsSpectrumListParser: single spectrum (list of length 1)
    t = QTable({'wavelength': [5000.0] * u.AA, 'flux': [1.0] * u.Jy})
    filepath = str(tmp_path / 'single_spec.ecsv')
    t.write(filepath, format='ascii.ecsv', overwrite=True)
    parser = SpecutilsSpectrumListParser(deconfigged_helper._app, filepath)
    assert parser._check_is_valid() == 'SpectrumList must contain more than one spectrum.'
