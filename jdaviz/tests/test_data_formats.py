
import pytest
import numpy as np
from astropy.io import fits
from jdaviz.core.data_formats import get_valid_format, identify_data
from jdaviz.core.config import list_configurations


def create_sdss(n_dim=2):
    """ create a fake SDSS single fiber spectral fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "SDSS 2.5-M", 'FIBERID': 555}))
    ext = fits.BinTableHDU(name='DATA', header=fits.Header({'TTYPE3': "ivar"}))
    hdulist = fits.HDUList([primary, ext])
    return hdulist


def create_manga(n_dim):
    """ create a fake SDSS MaNGA fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "SDSS 2.5-M"}))
    ext = fits.ImageHDU(name='FLUX', header=fits.Header({'INSTRUME': "MaNGA"}))
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1,)
    ext.data = np.empty(shape)
    hdulist = fits.HDUList([primary, ext])
    return hdulist


def create_jwst(n_dim):
    """ create a fake JWST fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "JWST"}))
    ext = fits.ImageHDU(name='ASDF')
    sci = fits.ImageHDU(name='SCI')
    exts = [primary, ext, sci]
    if n_dim == 1:
        ex1d = fits.ImageHDU(name='EXTRACT1D')
        exts.append(ex1d)
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1,)
    sci.data = np.empty(shape)
    hdulist = fits.HDUList(exts)
    return hdulist


def create_generic(n_dim=1):
    """ create a generic fits file of dimension N """
    primary = fits.PrimaryHDU()
    ext = fits.ImageHDU(name='DATA')
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1,)
    ext.data = np.empty(shape)
    hdulist = fits.HDUList([primary, ext])
    return hdulist


data = {'MaNGA cube': {'ndim': 3, 'fxn': create_manga},
        'MaNGA rss': {'ndim': 2, 'fxn': create_manga},
        'JWST s3d': {'ndim': 3, 'fxn': create_jwst},
        'JWST s2d': {'ndim': 2, 'fxn': create_jwst},
        'JWST x1d': {'ndim': 1, 'fxn': create_jwst},
        'SDSS-III/IV spec': {'ndim': 2, 'fxn': create_sdss},
        'generic 3d': {'ndim': 3, 'fxn': create_generic},
        'generic 1d': {'ndim': 1, 'fxn': create_generic}
        }


@pytest.fixture()
def create_fake_fits(tmp_path):
    """ fixture to create a fake FITS file in a temporary directory """
    def _create_fits(name):
        # generic fake file
        path = tmp_path / "fits"
        path.mkdir()
        filepath = path / (name.lower().replace('/', '_').replace(' ', '_') + '.fits')

        # generate fake fits.HDUList
        ndim = data[name]['ndim']
        fxn = data[name]['fxn']
        hdulist = fxn(n_dim=ndim)
        hdulist.writeto(filepath)
        return str(filepath)

    return _create_fits


@pytest.mark.parametrize('name, expconf',
                         [('MaNGA cube', 'cubeviz'),
                          ('MaNGA rss', 'imviz'),
                          ('JWST s3d', 'cubeviz'),
                          ('JWST s2d', 'specviz2d'),
                          ('JWST x1d', 'specviz'),
                          ('SDSS-III/IV spec', 'specviz'),
                          ('generic 3d', 'cubeviz'),
                          ('generic 1d', 'specviz')])
def test_get_valid_format(create_fake_fits, name, expconf):
    """ test correct file format and config is returned """
    filename = create_fake_fits(name)

    # for generic files that have no registered specutils format, valid_format will be blank
    name = name if 'generic' not in name else []

    valid_format, config = get_valid_format(filename)
    assert (valid_format, config) == (name, expconf)


def test_list_configurations():
    """ test correct configurations are listed """
    configs = list_configurations()
    assert set(configs).issubset({'default', 'cubeviz', 'specviz', 'mosviz', 'specviz2d'})


@pytest.mark.parametrize('name, expconf, expstat',
                         [('MaNGA cube', 'cubeviz', 'Success: Valid Format'),
                          ('MaNGA rss', 'imviz', 'Error: Config imviz not a valid configuration.'),
                          ('generic 1d', 'specviz', 'Error: Cannot determine format of '
                                                    'the file to load.')])
def test_identify_data(create_fake_fits, name, expconf, expstat):
    """ test correct status messages are returned with identify_data """
    filename = create_fake_fits(name)
    name = name if 'generic' not in name else []

    try:
        valid_format, config = identify_data(filename)
        status = 'Success: Valid Format'
    except ValueError as e:
        valid_format, config = name, expconf
        status = f'Error: {e}'
    assert (valid_format, config) == (name, expconf)
    assert expstat in status


def test_identify_current_mismatch(create_fake_fits):
    """ test correct mismatch config status """
    filename = create_fake_fits('MaNGA cube')
    with pytest.raises(ValueError,
                       match='Mismatch between input file format and loaded configuration.'):
        identify_data(filename, current='specviz')
