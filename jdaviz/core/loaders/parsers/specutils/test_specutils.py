import numpy as np
import astropy.units as u
from astropy.table import QTable

from jdaviz.core.loaders.parsers.specutils.specutils import (SpecutilsSpectrumArrayParser,
                                                             SpecutilsSpectrumListParser)


def test_specutils_parser_is_valid(deconfigged_helper, tmp_path, premade_spectrum_list):
    """Test _check_is_valid for specutils parsers: success and failure cases."""
    # SpecutilsSpectrumArrayParser success: valid 1D array
    parser = SpecutilsSpectrumArrayParser(deconfigged_helper._app, np.ones(10))
    assert parser._check_is_valid() == ''

    # SpecutilsSpectrumArrayParser failure: non-array and wrong dimensions
    for inp in ('not_an_array', np.ones((2, 2, 2, 2))):
        parser = SpecutilsSpectrumArrayParser(deconfigged_helper._app, inp)
        assert parser._check_is_valid() == ('Input must be a numpy array with '
                                            '1, 2, or 3 dimensions.')

    # SpecutilsSpectrumListParser success: inject a 2-spectrum list via cached_property
    parser = SpecutilsSpectrumListParser(deconfigged_helper._app, 'dummy')
    # bypass file I/O via cached_property injection
    parser.__dict__['output'] = premade_spectrum_list
    assert parser._check_is_valid() == ''

    # SpecutilsSpectrumListParser failure: single spectrum (list of length 1)
    t = QTable({'wavelength': [5000.0] * u.AA, 'flux': [1.0] * u.Jy})
    filepath = str(tmp_path / 'single_spec.ecsv')
    t.write(filepath, format='ascii.ecsv', overwrite=True)
    parser = SpecutilsSpectrumListParser(deconfigged_helper._app, filepath)
    assert parser._check_is_valid() == 'SpectrumList must contain more than one spectrum.'
