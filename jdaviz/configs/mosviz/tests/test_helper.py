import warnings
import astropy.units as u
import csv
import numpy as np
import pytest
from numpy.testing import assert_allclose
from astropy.nddata import CCDData
from astropy.wcs import WCS
from jdaviz.configs.mosviz.helper import Mosviz
from jdaviz.configs.specviz2d.helper import Specviz2d
from specutils import Spectrum1D, SpectrumCollection


@pytest.fixture
def mosviz_helper():
    return Mosviz()


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


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d]*5

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        result = SpectrumCollection.from_spectra(sc)
    return result


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
def test_viewer_axis_link(mosviz_helper, spectrum1d, spectrum2d):
    label1d = "Test 1D Spectrum"
    mosviz_helper.load_1d_spectra(spectrum1d, data_labels=label1d)

    label2d = "Test 2D Spectrum"
    mosviz_helper.load_2d_spectra(spectrum2d, data_labels=label2d)

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    scale_2d = mosviz_helper.app.get_viewer('spectrum-2d-viewer').scales['x']
    scale_1d = mosviz_helper.app.get_viewer('spectrum-viewer').scales['x']

    scale_2d.min = 200.0
    assert scale_1d.min == spectrum1d.spectral_axis.value[200]

    scale_1d.max = 7564
    assert scale_2d.max == 800.0


def test_to_csv(tmp_path, mosviz_helper, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_helper.load_1d_spectra(spectrum_collection, data_labels=labels)

    mosviz_helper.to_csv(filename=str(tmp_path / "MOS_data.csv"))

    found_rows = 0
    found_index_label = False

    with open(tmp_path / "MOS_data.csv", "r") as f:
        freader = csv.reader(f)
        for row in freader:
            if row[0] == "Table Index":
                found_index_label = True
            else:
                found_rows += 1

    assert found_index_label
    assert found_rows == 5


@pytest.mark.filterwarnings('ignore')
def test_table_scrolling(mosviz_helper, image, spectrum1d, spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=image)

    table = mosviz_helper.app.get_viewer('table-viewer')
    # first row is automatically selected in the UI
    # (otherwise it would be None which is a case not handled)
    table.widget_table.highlighted = 0
    table.next_row()
    assert table.widget_table.highlighted == 1
    table.next_row()
    # with only 2 rows, this should wrap back to 0
    assert table.widget_table.highlighted == 0
    table.prev_row()
    assert table.widget_table.highlighted == 1


@pytest.mark.filterwarnings('ignore')
def test_column_visibility(mosviz_helper, image, spectrum1d, spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=image)

    with pytest.raises(
                ValueError,
                match="visible must be one of None, True, or False."):
        mosviz_helper.get_column_names(visible='string')

    assert 'Redshift' not in mosviz_helper.get_column_names(True)
    assert 'Redshift' in mosviz_helper.get_column_names(False)
    assert 'Redshift' in mosviz_helper.get_column_names()

    mosviz_helper.show_column('Redshift')
    assert 'Redshift' in mosviz_helper.get_column_names(True)

    mosviz_helper.hide_column('Redshift')
    assert 'Redshift' not in mosviz_helper.get_column_names(True)


@pytest.mark.filterwarnings('ignore')
def test_custom_columns(mosviz_helper, image, spectrum1d, spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=image)

    mosviz_helper.add_column('custom_name')
    assert 'custom_name' in mosviz_helper.get_column_names(True)
    assert len(mosviz_helper.get_column('custom_name')) == 2

    mosviz_helper.update_column('custom_name', 0.1, row=1)
    assert mosviz_helper.get_column('custom_name')[1] == 0.1

    with pytest.raises(
                ValueError,
                match="row out of range of table"):
        mosviz_helper.update_column('custom_name', 0.3, row=3)

    with pytest.raises(
                ValueError,
                match="data must have length 2 \\(rows in table\\)"):
        mosviz_helper.add_column('custom_name_2', [0.1])

    mosviz_helper.show_column("Redshift")
    assert "Redshift" in mosviz_helper.get_column_names(True)
    mosviz_helper.set_visible_columns()
    assert "Redshift" not in mosviz_helper.get_column_names(True)


@pytest.mark.filterwarnings('ignore')
def test_redshift_column(mosviz_helper, image, spectrum1d, spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=image)

    mosviz_helper.update_column("Redshift", 0.1, row=0)
    assert_allclose(list(mosviz_helper.specviz.get_spectra().values())[0].redshift.value, 0.1)
    assert isinstance(mosviz_helper.specviz2d, Specviz2d)
    assert_allclose(mosviz_helper.get_spectrum_1d().redshift.value, 0.1)
    assert_allclose(mosviz_helper.get_spectrum_2d().redshift.value, 0.1)
    assert_allclose(mosviz_helper.get_spectrum_1d(row=1).redshift.value, 0.0)
