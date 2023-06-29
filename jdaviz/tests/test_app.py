import pytest

from jdaviz import Application, Specviz
from jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth import GaussianSmooth


# This applies to all viz but testing with Imviz should be enough.
def test_viewer_calling_app(imviz_helper):
    viewer = imviz_helper.default_viewer
    assert viewer.session.jdaviz_app is imviz_helper.app


def test_get_tray_item_from_name():
    app = Application(configuration='default')
    plg = app.get_tray_item_from_name('g-gaussian-smooth')
    assert isinstance(plg, GaussianSmooth)

    with pytest.raises(KeyError, match='not found in app'):
        app.get_tray_item_from_name('imviz-compass')


def test_nonstandard_specviz_viewer_name(spectrum1d):
    config = {'settings': {'configuration': 'nonstandard',
                           'data': {'parser': 'specviz-spectrum1d-parser'},
                           'visible': {'menu_bar': False,
                                       'toolbar': True,
                                       'tray': True,
                                       'tab_headers': False},
                           'context': {'notebook': {'max_height': '750px'}}},
              'toolbar': ['g-data-tools', 'g-subset-tools'],
              'tray': ['g-metadata-viewer',
                       'g-plot-options',
                       'g-subset-plugin',
                       'g-gaussian-smooth',
                       'g-model-fitting',
                       'g-unit-conversion',
                       'g-line-list',
                       'specviz-line-analysis',
                       'g-export-plot'],
              'viewer_area': [{'container': 'col',
                               'children': [{'container': 'row',
                                             'viewers': [{'name': 'H',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'h'},
                                                         {'name': 'K',
                                                          'plot': 'specviz-profile-viewer',
                                                          'reference': 'k'}]}]}]}

    class Customviz(Specviz):
        _default_configuration = config
        _default_spectrum_viewer_reference_name = 'h'

    viz = Customviz()
    assert viz.app.get_viewer_reference_names() == ['h', 'k']

    viz.load_data(spectrum1d, data_label='example label')
    with pytest.raises(ValueError):
        viz.get_data("non-existent label")


def test_duplicate_data_labels(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="test")
    specviz_helper.load_data(spectrum1d, data_label="test")
    dc = specviz_helper.app.data_collection
    assert dc[0].label == "test"
    assert dc[1].label == "test (1)"
    specviz_helper.load_data(spectrum1d, data_label="test_1")
    specviz_helper.load_data(spectrum1d, data_label="test")
    assert dc[2].label == "test_1"
    assert dc[3].label == "test (2)"


def test_duplicate_data_labels_with_brackets(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="test[test]")
    specviz_helper.load_data(spectrum1d, data_label="test[test]")
    dc = specviz_helper.app.data_collection
    assert len(dc) == 2
    assert dc[0].label == "test[test]"
    assert dc[1].label == "test[test] (1)"


def test_return_data_label_is_none(specviz_helper):
    data_label = specviz_helper.app.return_data_label(None)
    assert data_label == "Unknown"


def test_return_data_label_is_image(specviz_helper):
    data_label = specviz_helper.app.return_data_label("data/path/test.jpg")
    assert data_label == "test[jpg]"


def test_hdulist_with_filename(cubeviz_helper, image_cube_hdu_obj):
    image_cube_hdu_obj.file_name = "test"
    data_label = cubeviz_helper.app.return_data_label(image_cube_hdu_obj)
    assert data_label == "test[HDU object]"


def test_file_path_not_image(imviz_helper, tmp_path):
    path = tmp_path / "myimage.fits"
    path.touch()
    data_label = imviz_helper.app.return_data_label(str(path))
    assert data_label == "myimage"


def test_unique_name_variations(specviz_helper, spectrum1d):
    data_label = specviz_helper.app.return_unique_name(None)
    assert data_label == "Unknown"

    specviz_helper.load_data(spectrum1d, data_label="test[flux]")
    data_label = specviz_helper.app.return_data_label("test[flux]", ext="flux")
    assert data_label == "test[flux][flux]"

    data_label = specviz_helper.app.return_data_label("test", ext="flux")
    assert data_label == "test[flux] (1)"


def test_substring_in_label(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="M31")
    specviz_helper.load_data(spectrum1d, data_label="M32")
    data_label = specviz_helper.app.return_data_label("M")
    assert data_label == "M"


@pytest.mark.parametrize('data_label', ('111111', 'aaaaa', '///(#$@)',
                                        'two  spaces  repeating',
                                        'word42word42word  two  spaces'))
def test_edge_cases(specviz_helper, spectrum1d, data_label):
    dc = specviz_helper.app.data_collection

    specviz_helper.load_data(spectrum1d, data_label=data_label)
    specviz_helper.load_data(spectrum1d, data_label=data_label)
    assert dc[1].label == f"{data_label} (1)"

    specviz_helper.load_data(spectrum1d, data_label=data_label)
    assert dc[2].label == f"{data_label} (2)"


def test_case_that_used_to_break_return_label(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label="this used to break (1)")
    specviz_helper.load_data(spectrum1d, data_label="this used to break")
    dc = specviz_helper.app.data_collection
    assert dc[0].label == "this used to break (1)"
    assert dc[1].label == "this used to break (2)"
