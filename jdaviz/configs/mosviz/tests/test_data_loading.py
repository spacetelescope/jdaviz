# Tests data loading in the Mosviz Jdaviz configuration

import pathlib
from tempfile import gettempdir
from zipfile import ZipFile

from astropy.nddata import CCDData
from astropy.utils.data import download_file
import numpy as np
import pytest
from specutils import Spectrum1D


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
def test_load_image(mosviz_helper, mos_image):
    label = "Test Image"
    mosviz_helper.load_images(mos_image, data_labels=label)

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
def test_load_mos_spectrum2d(mosviz_helper, mos_spectrum2d):

    label = "Test 2D Spectrum"
    mosviz_helper.load_2d_spectra(mos_spectrum2d, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    assert mosviz_helper.app.data_collection[0].label == label

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-2d-viewer')

    assert list(data.values())[0].shape == (1024, 15)
    assert list(data.keys())[0] == label


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d]*3
    spectra2d = [mos_spectrum2d]*3
    images = [mos_image]*3

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
def test_load_single_image_multi_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match='The dimensions of component 2D Spectra are incompatible'):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[])

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3


@pytest.mark.filterwarnings('ignore')
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
    with pytest.warns(UserWarning, match="Unspecific or Unrecognized MOS Instrument"):
        mosviz_helper.load_data(directory=data_dir)

    assert len(mosviz_helper.app.data_collection) == 16
    assert "MOS Table" in mosviz_helper.app.data_collection
    assert "Image 4" in mosviz_helper.app.data_collection
    assert "1D Spectrum 4" in mosviz_helper.app.data_collection
    assert "2D Spectrum 4" in mosviz_helper.app.data_collection


def test_zip_error(mosviz_helper):
    '''
    Zipfiles are explicitly and intentionally not supported. This test confirms a TypeError is
    raised if the user tries to supply a Zipfile and expects Mosviz to autoextract.
    '''
    zip_path = pathlib.Path(gettempdir(), "jdaviz_test_zip.zip")
    zip = ZipFile(zip_path, mode='w')
    zip.close()

    with pytest.raises(TypeError, match="Please extract"):
        mosviz_helper.load_data(str(zip_path))
