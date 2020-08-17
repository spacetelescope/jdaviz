import astropy.units as u
import numpy as np
import pytest
from astropy.nddata import CCDData
from astropy.wcs import WCS
from jdaviz.configs.mosviz.helper import MosViz
from spectral_cube import SpectralCube
from specutils import Spectrum1D, SpectrumCollection


@pytest.fixture
def mosviz_app():
    return MosViz()


@pytest.fixture
def spectrum1d():
    spec_axis = np.linspace(6000, 8000, 1024) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    return Spectrum1D(spectral_axis=spec_axis, flux=flux)


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
    data = np.random.sample((15, 1, 1174))
    spectral_cube = SpectralCube(data, wcs=wcs)

    return spectral_cube


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d for _ in range(5)]

    return SpectrumCollection.from_spectra(sc)


@pytest.fixture
def image():
    header = """
WCSAXES =                    2 / Number of coordinate axes
CRPIX1  =                937.0 / Pixel coordinate of reference point
CRPIX2  =                696.0 / Pixel coordinate of reference point
CDELT1  = -1.5182221158397E-05 / [deg] Coordinate increment at reference point
CDELT2  =  1.5182221158397E-05 / [deg] Coordinate increment at reference point
CUNIT1  = 'deg'                / Units of coordinate increment and value
CUNIT2  = 'deg'                / Units of coordinate increment and value
CTYPE1  = 'RA---TAN'           / Right ascension, gnomonic projection
CTYPE2  = 'DEC--TAN'           / Declination, gnomonic projection
CRVAL1  =      5.0155198140981 / [deg] Coordinate value at reference point
CRVAL2  =       5.002450989248 / [deg] Coordinate value at reference point
LONPOLE =                180.0 / [deg] Native longitude of celestial pole
LATPOLE =       5.002450989248 / [deg] Native latitude of celestial pole
DATEREF = '1858-11-17'         / ISO-8601 fiducial time
MJDREFI =                  0.0 / [d] MJD of fiducial time, integer part
MJDREFF =                  0.0 / [d] MJD of fiducial time, fractional part
RADESYS = 'ICRS'               / Equatorial coordinate system
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


def test_load_spectrum1d(mosviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_app.load_1d_spectra(spectrum1d, data_labels=label)

    assert len(mosviz_app.app.data_collection) == 2
    assert mosviz_app.app.data_collection[0].label == label

    table = mosviz_app.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == label

    with pytest.raises(TypeError) as e:
        mosviz_app.load_1d_spectra([1, 2, 3])


def test_load_spectrum_collection(mosviz_app, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_app.load_1d_spectra(spectrum_collection, data_labels=labels)

    assert len(mosviz_app.app.data_collection) == 6
    assert mosviz_app.app.data_collection[0].label == labels[0]

    table = mosviz_app.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == labels[0]


def test_load_list_of_spectrum1d(mosviz_app, spectrum1d):
    spectra = [spectrum1d for _ in range(3)]

    labels = [f"Test Spectrum 1D {i}" for i in range(3)]
    mosviz_app.load_1d_spectra(spectra, data_labels=labels)

    assert len(mosviz_app.app.data_collection) == 4
    assert mosviz_app.app.data_collection[0].label == labels[0]

    table = mosviz_app.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == labels[0]


def test_load_spectrum2d(mosviz_app, spectrum2d):
    label = "Test 2D Spectrum"
    mosviz_app.load_2d_spectra(spectrum2d, data_labels=label)

    assert len(mosviz_app.app.data_collection) == 2
    assert mosviz_app.app.data_collection[0].label == label

    table = mosviz_app.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_app.app.get_data_from_viewer('spectrum-2d-viewer')

    assert list(data.values())[0].shape == (15, 1, 1174)
    assert list(data.keys())[0] == label


def test_load_image(mosviz_app, image):
    label = "Test Image"
    mosviz_app.load_images(image, data_labels=label)

    assert len(mosviz_app.app.data_collection) == 2
    assert mosviz_app.app.data_collection[0].label == f"{label} 0"

    table = mosviz_app.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_app.app.get_data_from_viewer('image-viewer')

    # assert isinstance(list(data.values())[0], CCDData)
    assert list(data.values())[0].shape == (55, 55)
    assert list(data.keys())[0] == f"{label} 0"
