# Tests data loading in the Mosviz Jdaviz configuration

from zipfile import ZipFile

from astropy.nddata import CCDData
import numpy as np
import pytest
from specutils import Spectrum1D

from jdaviz.utils import PRIHDR_KEY


def test_load_spectrum1d(mosviz_helper, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_helper.load_data(spectra_1d=spectrum1d, spectra_1d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == label
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[label], Spectrum1D)

    with pytest.raises(AttributeError):
        mosviz_helper.load_1d_spectra([1, 2, 3])


@pytest.mark.filterwarnings('ignore')
def test_load_image(mosviz_helper, mos_image):
    label = "Test Image"
    mosviz_helper.load_images(mos_image, data_labels=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == f"{label} 0"
    assert PRIHDR_KEY not in dc_0.meta
    assert dc_0.meta['RADESYS'] == 'ICRS'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('image-viewer')

    dataval = data[f"{label} 0"]
    assert isinstance(dataval, CCDData)
    assert dataval.shape == (55, 55)


def test_load_spectrum_collection(mosviz_helper, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_helper.load_1d_spectra(spectrum_collection, data_labels=labels)

    # +1 for the table viewer
    assert len(mosviz_helper.app.data_collection) == len(spectrum_collection) + 1
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == labels[0]
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.select_row(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[labels[0]], Spectrum1D)


def test_load_list_of_spectrum1d(mosviz_helper, spectrum1d):
    spectra = [spectrum1d] * 3

    labels = [f"Test Spectrum 1D {i}" for i in range(3)]
    mosviz_helper.load_1d_spectra(spectra, data_labels=labels)

    assert len(mosviz_helper.app.data_collection) == 4
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == labels[0]
    assert dc_0.meta['uncertainty_type'] == 'std'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(data[labels[0]], Spectrum1D)


@pytest.mark.filterwarnings('ignore')
def test_load_mos_spectrum2d(mosviz_helper, mos_spectrum2d):

    label = "Test 2D Spectrum"
    mosviz_helper.load_data(spectra_2d=mos_spectrum2d, spectra_2d_label=label)

    assert len(mosviz_helper.app.data_collection) == 2
    dc_0 = mosviz_helper.app.data_collection[0]
    assert dc_0.label == label
    assert dc_0.meta['INSTRUME'] == 'nirspec'

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    data = mosviz_helper.app.get_data_from_viewer('spectrum-2d-viewer')

    assert data[label].shape == (1024, 15)


@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_multi_image_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra1d, spectra2d, images=images, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 10

    qtable = mosviz_helper.to_table()
    if label is None:
        assert qtable["Images"][0] == "Image 0"
    else:
        assert qtable["Images"][0] == "Test Label 0"


def test_load_multi_image_and_spec1d_only(mosviz_helper, mos_image, spectrum1d):
    spectra1d = [spectrum1d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra_1d=spectra1d, images=images)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


def test_load_multi_image_and_spec2d_only(mosviz_helper, mos_image, mos_spectrum2d):
    spectra2d = [mos_spectrum2d] * 3
    images = [mos_image] * 3

    mosviz_helper.load_data(spectra_2d=spectra2d, images=images)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 7


@pytest.mark.parametrize('label', [None, "Test Label"])
def test_load_single_image_multi_spec(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d, label):
    spectra1d = [spectrum1d] * 3
    spectra2d = [mos_spectrum2d] * 3

    image_viewer = mosviz_helper.app.get_viewer('image-viewer')

    # Coordinates info panel should not crash even when nothing is loaded.
    image_viewer.on_mouse_or_key_event({'event': 'mouseover'})
    assert image_viewer.label_mouseover is None

    # Test that loading is still possible after previous crash:
    # https://github.com/spacetelescope/jdaviz/issues/364
    with pytest.raises(ValueError, match="No data found with the label 'MOS Table'"):
        mosviz_helper.load_data(spectra1d, spectra2d, images=[])

    with pytest.warns(UserWarning, match='Could not parse metadata from input images'):
        mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image, images_label=label)

    assert mosviz_helper.app.get_viewer("table-viewer").figure_widget.highlighted == 0
    assert len(mosviz_helper.app.data_collection) == 8

    qtable = mosviz_helper.to_table()
    if label is None:
        assert np.all(qtable["Images"] == "Shared Image")
    else:
        assert np.all(qtable["Images"] == "Test Label")
    assert len(qtable) == 3

    # Also check coordinates info panels for Mosviz image viewer.
    # 1D spectrum viewer panel is already tested in Specviz.
    # 2D spectrum viewer panel is already tested in Specviz2d.

    image_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert image_viewer.label_mouseover.pixel == 'x=000.0 y=000.0'
    assert image_viewer.label_mouseover.value == '+3.74540e-01 Jy'
    assert image_viewer.label_mouseover.world_ra_deg == '5.0297844783'
    assert image_viewer.label_mouseover.world_dec_deg == '4.9918991917'

    image_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': None, 'y': 0}})
    assert image_viewer.label_mouseover.pixel == ''
    assert image_viewer.label_mouseover.value == ''
    assert image_viewer.label_mouseover.world_ra_deg == ''
    assert image_viewer.label_mouseover.world_dec_deg == ''

    image_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert image_viewer.label_mouseover.pixel == 'x=-01.0 y=000.0'
    assert image_viewer.label_mouseover.value == ''
    assert image_viewer.label_mouseover.world_ra_deg == '5.0297997183'
    assert image_viewer.label_mouseover.world_dec_deg == '4.9918991914'

    image_viewer.on_mouse_or_key_event({'event': 'mouseleave'})
    assert image_viewer.label_mouseover.pixel == ''
    assert image_viewer.label_mouseover.value == ''
    assert image_viewer.label_mouseover.world_ra_deg == ''
    assert image_viewer.label_mouseover.world_dec_deg == ''


def test_zip_error(mosviz_helper, tmp_path):
    '''
    Zipfiles are explicitly and intentionally not supported. This test confirms a TypeError is
    raised if the user tries to supply a Zipfile and expects Mosviz to autoextract.
    '''
    zip_path = tmp_path / "jdaviz_test_zip.zip"
    zip = ZipFile(zip_path, mode='w')
    zip.close()

    with pytest.raises(TypeError, match="Please extract"):
        mosviz_helper.load_data(directory=str(zip_path))
