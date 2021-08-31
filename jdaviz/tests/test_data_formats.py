
import pytest
import numpy as np
from astropy.io import fits
from jdaviz.core.data_formats import get_valid_format, identify_data
from jdaviz.core.config import list_configurations


def create_sdss(n_dim=2, **kwargs):
    """ create a fake SDSS single fiber spectral fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "SDSS 2.5-M", 'FIBERID': 555}))
    ext = fits.BinTableHDU(name='DATA', header=fits.Header({'TTYPE3': "ivar"}))
    return fits.HDUList([primary, ext])


def create_manga(n_dim=None, **kwargs):
    """ create a fake SDSS MaNGA fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "SDSS 2.5-M"}))
    ext = fits.ImageHDU(name='FLUX', header=fits.Header({'INSTRUME': "MaNGA"}))
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1,)
    ext.data = np.empty(shape)
    return fits.HDUList([primary, ext])


def _create_bintable(name, ver=1):
    return fits.BinTableHDU.from_columns(
                [fits.Column(name='target', format='20A', array=np.ones(3)),
                 fits.Column(name='V_mag', format='E', array=np.ones(3))],
                name=name, ver=ver
            )


def create_jwst(n_dim=None, multi=None, ext=None):
    """ create a fake JWST fits file """
    primary = fits.PrimaryHDU(header=fits.Header({'TELESCOP': "JWST"}))
    asdf = fits.ImageHDU(name='ASDF')
    sci = fits.ImageHDU(name='SCI')
    exts = [primary]
    if n_dim == 1:
        ex1d = _create_bintable(ext, ver=1)
        exts.append(ex1d)
        # create two more extensions
        if multi:
            for i in range(1, 3):
                ex1d = _create_bintable(ext, ver=i)
                exts.append(ex1d)
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1, )
    sci.data = np.empty(shape)
    if n_dim > 1:
        exts.append(sci)
    exts.append(asdf)
    return fits.HDUList(exts)


def create_generic(n_dim=1, **kwargs):
    """ create a generic fits file of dimension N """
    primary = fits.PrimaryHDU()
    ext = fits.ImageHDU(name='DATA')
    shape = (1,) if n_dim == 1 else (1, 2,) if n_dim == 2 else (1, 2, 3) if n_dim == 3 else (1,)
    ext.data = np.empty(shape)
    return fits.HDUList([primary, ext])


data = {'MaNGA cube': {'ndim': 3, 'fxn': create_manga},
        'MaNGA rss': {'ndim': 2, 'fxn': create_manga},
        'JWST s3d': {'ndim': 3, 'fxn': create_jwst},
        'JWST s2d': {'ndim': 2, 'fxn': create_jwst},
        'JWST x1d': {'ndim': 1, 'fxn': create_jwst},
        'JWST c1d': {'ndim': 1, 'fxn': create_jwst, 'ext': 'COMBINE1D'},
        'JWST x1d multi': {'ndim': 1, 'fxn': create_jwst, 'multi': True},
        'JWST c1d multi': {'ndim': 1, 'fxn': create_jwst, 'ext': 'COMBINE1D', 'multi': True},
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
        multi = data[name].get('multi', None)
        ext = data[name].get('ext', 'EXTRACT1D')
        hdulist = fxn(n_dim=ndim, ext=ext, multi=multi)
        hdulist.writeto(filepath)
        return str(filepath)

    return _create_fits


@pytest.mark.parametrize('name, expconf',
                         [('MaNGA cube', 'cubeviz'),
                          ('MaNGA rss', 'specviz'),
                          ('JWST s3d', 'cubeviz'),
                          ('JWST s2d', 'specviz2d'),
                          ('JWST x1d', 'specviz'),
                          ('JWST c1d', 'specviz'),
                          ('JWST x1d multi', 'specviz'),
                          ('JWST c1d multi', 'specviz'),
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
    assert set(configs).issubset({'default', 'cubeviz', 'specviz', 'mosviz',
                                  'imviz', 'specviz2d'})


@pytest.mark.parametrize('name, expconf, expstat',
                         [('MaNGA cube', 'cubeviz', 'Success: Valid Format'),
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
