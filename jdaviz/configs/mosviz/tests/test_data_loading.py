from zipfile import ZipFile
import pathlib

from astropy.nddata import CCDData
import astropy.units as u
from astropy.utils.data import download_file
from astropy.wcs import WCS
import numpy as np
import pytest
from jdaviz.configs.mosviz.helper import Mosviz
from specutils import Spectrum1D


@pytest.fixture
def mosviz_helper():
    return Mosviz()


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
WCSAXES =                    2 / Number of coordinate axes
CRPIX1  =                  0.0 / Pixel coordinate of reference point
CRPIX2  =               1024.5 / Pixel coordinate of reference point
CDELT1  =                1E-06 / [m] Coordinate increment at reference point
CDELT2  =  2.9256727777778E-05 / [deg] Coordinate increment at reference point
CUNIT1  = 'm'                  / Units of coordinate increment and value
CUNIT2  = 'deg'                / Units of coordinate increment and value
CTYPE1  = 'WAVE'               / Vacuum wavelength (linear)
CTYPE2  = 'OFFSET'             / Spatial offset
CRVAL1  =                  0.0 / [m] Coordinate value at reference point
CRVAL2  =                  5.0 / [deg] Coordinate value at reference point
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
    data = np.random.sample((1024, 15)) * u.one
    spectral_cube = Spectrum1D(data, wcs=wcs)

    return spectral_cube


def test_load_spectrum1d(mosviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_helper.load_1d_spectra(spectrum1d, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == label

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == label

    with pytest.raises(TypeError):
        mosviz_helper.load_1d_spectra([1, 2, 3])


@pytest.mark.filterwarnings('ignore')
def test_load_image(mosviz_helper, image):
    label = "Test Image"
    mosviz_helper.load_images(image, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == f"{label} 0"

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('image-viewer')

    assert isinstance(list(data.values())[0], CCDData)
    assert list(data.values())[0].shape == (55, 55)
    assert list(data.keys())[0] == f"{label} 0"


def test_load_spectrum_collection(mosviz_helper, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_helper.load_1d_spectra(spectrum_collection, data_labels=labels)

    assert len(mosviz_helper.app.data_collection) == 6
    assert mosviz_helper.app.data_collection[0].label == labels[0]

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == labels[0]


def test_load_list_of_spectrum1d(mosviz_helper, spectrum1d):
    spectra = [spectrum1d]*3

    labels = [f"Test Spectrum 1D {i}" for i in range(3)]
    mosviz_helper.load_1d_spectra(spectra, data_labels=labels)

    assert len(mosviz_helper.app.data_collection) == 4
    assert mosviz_helper.app.data_collection[0].label == labels[0]

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == labels[0]


@pytest.mark.filterwarnings('ignore')
def test_load_spectrum2d(mosviz_helper, spectrum2d):

    label = "Test 2D Spectrum"
    mosviz_helper.load_2d_spectra(spectrum2d, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == label

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-2d-viewer')

    assert list(data.values())[0].shape == (1024, 15)
    assert list(data.keys())[0] == label


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, image, spectrum1d, spectrum2d, label):
    spectra1d = [spectrum1d]*3
    spectra2d = [spectrum2d]*3
    images = [image]*3

    mosviz_helper.load_data(spectra1d, spectra2d, images=images, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 10

    qtable = mosviz_helper.to_table()
    if label is None:
        assert qtable["Images"][0] == "Image 0"
    else:
        assert qtable["Images"][0] == "Test Label 0"


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_single_image_multi_spec(mosviz_helper, image, spectrum1d, spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [spectrum2d] * 3

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match='The dimensions of component 2D Spectra are incompatible'):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[])

    mosviz_helper.load_data(spectra1d, spectra2d, images=image, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3


@pytest.mark.remote_data
def test_nirpsec_loader(mosviz_helper, tmpdir):
    '''
    Tests loading our default MosvizExample notebook data
    '''

    test_data = 'https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'mosviz_nirspec_data_0.3' / 'level3')

    data_dir = level3_path

    mosviz_helper.load_data(directory=data_dir, instrument='nirspec')

    assert len(mosviz_helper.app.data_collection) == 16
    assert "MOS Table" in mosviz_helper.app.data_collection
    assert "Image 4" in mosviz_helper.app.data_collection
    assert "1D Spectrum 4" in mosviz_helper.app.data_collection
    assert "2D Spectrum 4" in mosviz_helper.app.data_collection


@pytest.mark.remote_data
def test_niriss_loader(mosviz_helper, tmpdir):

    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'NIRISS_for_parser_p0171')

    data_dir = level3_path

    mosviz_helper.load_data(directory=data_dir, instrument='niriss')

    assert len(mosviz_helper.app.data_collection) == 80
    assert mosviz_helper.app.data_collection[0].label == "Image canucs F150W"
    assert mosviz_helper.app.data_collection[-1].label == "MOS Table"


@pytest.mark.remote_data
def test_nirpsec_fallback(mosviz_helper, tmpdir):
    '''
    When no instrument is provided, mosviz.load_data is expected to fallback to the nirspec loader.
    Naturally, the nirspec dataset should then work without any instrument keyword
    '''

    test_data = 'https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir)

    level3_path = (pathlib.Path(tmpdir) / 'mosviz_nirspec_data_0.3' / 'level3')

    data_dir = level3_path

    mosviz_helper.load_data(directory=data_dir)

    assert len(mosviz_helper.app.data_collection) == 16
    assert "MOS Table" in mosviz_helper.app.data_collection
    assert "Image 4" in mosviz_helper.app.data_collection
    assert "1D Spectrum 4" in mosviz_helper.app.data_collection
    assert "2D Spectrum 4" in mosviz_helper.app.data_collection
