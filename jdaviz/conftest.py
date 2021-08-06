# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from specutils import Spectrum1D
from spectral_cube import SpectralCube
from astropy.nddata import CCDData


from jdaviz import __version__, CubeViz, Imviz, MosViz, SpecViz, Specviz2d

SPECTRUM_SIZE = 10  # length of spectrum


@pytest.fixture
def cubeviz_app():
    return CubeViz()


@pytest.fixture
def imviz_app():
    return Imviz()


@pytest.fixture
def mosviz_app():
    return MosViz()


@pytest.fixture
def specviz_app():
    return SpecViz()


@pytest.fixture
def specviz2d_app():
    return Specviz2d()


@pytest.fixture
def spectral_cube_wcs(request):
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'RA---TAN', 'DEC--TAN', 'FREQ'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def spectrum1d():
    np.random.seed(42)

    spec_axis = np.linspace(6000, 8000, SPECTRUM_SIZE) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy
    uncertainty = StdDevUncertainty(np.abs(np.random.randn(len(spec_axis.value))) * u.Jy)

    return Spectrum1D(spectral_axis=spec_axis, flux=flux, uncertainty=uncertainty)


@pytest.fixture
def spectrum2d():
    header = """
WCSAXES =                    3 / Number of coordinate axes
CRPIX1  =               1024.5 / Pixel coordinate of reference point
CRPIX2  =               1024.5 / Pixel coordinate of reference point
CRPIX3  =                  0.0 / Pixel coordinate of reference point
PC1_1   =                 -1.0 / Coordinate transformation matrix element
PC3_1   =                  1.0 / Coordinate transformation matrix element
CDELT1  =  2.8685411111111E-05 / [deg] Coordinate increment at reference point
CDELT2  =  2.9256727777778E-05 / [deg] Coordinate increment at reference point
CDELT3  =                1E-06 / [m] Coordinate increment at reference point
CUNIT1  = 'deg'                / Units of coordinate increment and value
CUNIT2  = 'deg'                / Units of coordinate increment and value
CUNIT3  = 'm'                  / Units of coordinate increment and value
CTYPE1  = 'RA---TAN'           / Right ascension, gnomonic projection
CTYPE2  = 'DEC--TAN'           / Declination, gnomonic projection
CTYPE3  = 'WAVE'               / Vacuum wavelength (linear)
CRVAL1  =                  5.0 / [deg] Coordinate value at reference point
CRVAL2  =                  5.0 / [deg] Coordinate value at reference point
CRVAL3  =                  0.0 / [m] Coordinate value at reference point
LONPOLE =                180.0 / [deg] Native longitude of celestial pole
LATPOLE =                  5.0 / [deg] Native latitude of celestial pole
MJDREFI =                  0.0 / [d] MJD of fiducial time, integer part
MJDREFF =                  0.0 / [d] MJD of fiducial time, fractional part
RADESYS = 'ICRS'               / Equatorial coordinate system
SPECSYS = 'BARYCENT'           / Reference frame of spectral coordinates
S_REGION= 'POLYGON ICRS  5.029236065 4.992154276 5.029513148 '
          '4.992154276 5.029513148 4.992468585 5.029236065 4.992468585'
INSTRUME= 'NIRSpec
"""
    new_hdr = {}

    for line in header.split('\n'):
        try:
            key, value = line.split('=')
            key = key.strip()
            value, _ = value.split('/')
            value = value.strip()
            value = value.strip("'")
        except ValueError:
            continue

        new_hdr[key] = value

    wcs = WCS(new_hdr)
    data = np.random.sample((15, 1, SPECTRUM_SIZE))
    spectral_cube = SpectralCube(data, wcs=wcs)
    spectral_cube.meta['INSTRUME'] = 'NIRSpec'

    return spectral_cube


@pytest.fixture
def image():
    header = """
WCSAXES =                    3 / Number of coordinate axes
CRPIX1  =               1024.5 / Pixel coordinate of reference point
CRPIX2  =               1024.5 / Pixel coordinate of reference point
CRPIX3  =                  0.0 / Pixel coordinate of reference point
PC1_1   =                 -1.0 / Coordinate transformation matrix element
PC3_1   =                  1.0 / Coordinate transformation matrix element
CDELT1  =  2.8685411111111E-05 / [deg] Coordinate increment at reference point
CDELT2  =  2.9256727777778E-05 / [deg] Coordinate increment at reference point
CDELT3  =                1E-06 / [m] Coordinate increment at reference point
CUNIT1  = 'deg'                / Units of coordinate increment and value
CUNIT2  = 'deg'                / Units of coordinate increment and value
CUNIT3  = 'm'                  / Units of coordinate increment and value
CTYPE1  = 'RA---TAN'           / Right ascension, gnomonic projection
CTYPE2  = 'DEC--TAN'           / Declination, gnomonic projection
CTYPE3  = 'WAVE'               / Vacuum wavelength (linear)
CRVAL1  =                  5.0 / [deg] Coordinate value at reference point
CRVAL2  =                  5.0 / [deg] Coordinate value at reference point
CRVAL3  =                  0.0 / [m] Coordinate value at reference point
LONPOLE =                180.0 / [deg] Native longitude of celestial pole
LATPOLE =       5.002450989248 / [deg] Native latitude of celestial pole
DATEREF = '1858-11-17'         / ISO-8601 fiducial time
MJDREFI =                  0.0 / [d] MJD of fiducial time, integer part
MJDREFF =                  0.0 / [d] MJD of fiducial time, fractional part
RADESYS = 'ICRS'               / Equatorial coordinate system
SIMPLE  =                    T / conforms to FITS standard                      
BITPIX  =                  -64 / array data type                                
NAXIS   =                    3 / number of array dimensions                     
NAXIS1  =                   55                                                  
NAXIS2  =                   55                        
NAXIS3  =                    1                          
EXTEND  =                    T                                                       
OBJ_RA  =    5.029374606669549 / Cutout object RA in deg                        
OBJ_DEC =      4.9923114303282 / Cutout object DEC in deg   
"""
    new_hdr = {}

    for line in header.split('\n'):
        try:
            key, value = line.split('=')
            key = key.strip()
            value, _ = value.split('/')
            value = value.strip()
            value = value.strip("'")
        except ValueError:
            continue

        new_hdr[key] = value

    wcs = WCS(new_hdr)
    data = np.random.sample((55, 55))
    ccd_data = CCDData(data, wcs=wcs, unit='Jy')

    return ccd_data

try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}


def pytest_configure(config):
    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'
    PYTEST_HEADER_MODULES['specutils'] = 'specutils'
    PYTEST_HEADER_MODULES['spectral-cube'] = 'spectral_cube'
    PYTEST_HEADER_MODULES['asteval'] = 'asteval'
    PYTEST_HEADER_MODULES['click'] = 'click'
    PYTEST_HEADER_MODULES['echo'] = 'echo'
    PYTEST_HEADER_MODULES['idna'] = 'idna'
    PYTEST_HEADER_MODULES['traitlets'] = 'traitlets'
    PYTEST_HEADER_MODULES['bqplot'] = 'bqplot'
    PYTEST_HEADER_MODULES['bqplot-image-gl'] = 'bqplot_image_gl'
    PYTEST_HEADER_MODULES['glue-core'] = 'glue'
    PYTEST_HEADER_MODULES['glue-jupyter'] = 'glue_jupyter'
    PYTEST_HEADER_MODULES['glue-astronomy'] = 'glue_astronomy'
    PYTEST_HEADER_MODULES['ipyvue'] = 'ipyvue'
    PYTEST_HEADER_MODULES['ipyvuetify'] = 'ipyvuetify'
    PYTEST_HEADER_MODULES['ipysplitpanes'] = 'ipysplitpanes'
    PYTEST_HEADER_MODULES['ipygoldenlayout'] = 'ipygoldenlayout'
    PYTEST_HEADER_MODULES['voila'] = 'voila'
    PYTEST_HEADER_MODULES['vispy'] = 'vispy'
    PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
    PYTEST_HEADER_MODULES['asdf'] = 'asdf'
    PYTEST_HEADER_MODULES['jwst'] = 'jwst'

    TESTED_VERSIONS['jdaviz'] = __version__

# TODO: Need to handle warnings properly first before we can enable this. See
# https://github.com/spacetelescope/jdaviz/issues/478
# Uncomment the last two lines in this block to treat all DeprecationWarnings as
# exceptions.
# from astropy.tests.helper import enable_deprecations_as_exceptions  # noqa
# enable_deprecations_as_exceptions()
