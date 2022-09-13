# Tests all non-data-loading functionality of the Mosviz Helper class
# For data-loading tests, see test_data_loading.py

import csv
import pytest
from numpy.testing import assert_allclose
from jdaviz.configs.specviz2d.helper import Specviz2d


@pytest.mark.filterwarnings('ignore')
def test_viewer_axis_link(mosviz_helper, mos_spectrum1d, mos_spectrum2d):
    label1d = "Test 1D Spectrum"
    mosviz_helper.load_1d_spectra(mos_spectrum1d, data_labels=label1d)

    label2d = "Test 2D Spectrum"
    mosviz_helper.load_2d_spectra(mos_spectrum2d, data_labels=label2d)

    table = mosviz_helper.app.get_viewer('table-viewer')
    table.widget_table.vue_on_row_clicked(0)

    scale_2d = mosviz_helper.app.get_viewer('spectrum-2d-viewer').scales['x']
    scale_1d = mosviz_helper.app.get_viewer('spectrum-viewer').scales['x']

    scale_2d.min = 200.0
    assert scale_1d.min == mos_spectrum1d.spectral_axis.value[200]

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
def test_table_scrolling(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [mos_spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image)

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
def test_column_visibility(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [mos_spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image)

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
def test_custom_columns(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [mos_spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image)

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
def test_redshift_column(mosviz_helper, mos_image, spectrum1d, mos_spectrum2d):
    spectra1d = [spectrum1d] * 2
    spectra2d = [mos_spectrum2d] * 2

    mosviz_helper.load_data(spectra1d, spectra2d, images=mos_image)

    mosviz_helper.update_column("Redshift", 0.1, row=0)
    assert_allclose(list(mosviz_helper.specviz.get_spectra().values())[0].redshift.value, 0.1)
    assert isinstance(mosviz_helper.specviz2d, Specviz2d)
    assert_allclose(mosviz_helper.get_spectrum_1d().redshift.value, 0.1)
    assert_allclose(mosviz_helper.get_spectrum_2d().redshift.value, 0.1)
    assert_allclose(mosviz_helper.get_spectrum_1d(row=1).redshift.value, 0.0)


def test_plugin_user_apis(mosviz_helper):
    for plugin_name, plugin_api in mosviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)
