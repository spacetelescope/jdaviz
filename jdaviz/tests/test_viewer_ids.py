from jdaviz import Application


def test_default_viewer_ids_default():
    app = Application(configuration='default')
    assert app.get_viewer_reference_names() == []
    assert app.get_viewer_ids() == []


# NOTE: Unable to parametrize fixture as input.

def test_default_viewer_ids_cubeviz(cubeviz_helper):
    x = cubeviz_helper.app
    assert sorted(x.get_viewer_reference_names()) == [
        'flux-viewer', 'spectrum-viewer', 'uncert-viewer']
    assert x.get_viewer_ids() == ['cubeviz-0', 'cubeviz-1', 'cubeviz-2']


def test_default_viewer_ids_imviz(imviz_helper):
    x = imviz_helper.app
    assert x.get_viewer_reference_names() == ['imviz-0']
    assert x.get_viewer_ids() == ['imviz-0']
    assert x.get_viewer_ids(prefix='imviz') == ['imviz-0']
    assert x.get_viewer_ids(prefix='specviz') == []

    viewer = x.get_viewer('imviz-0')
    assert x.get_viewer_by_id('imviz-0') is viewer


def test_default_viewer_ids_mosviz(mosviz_helper):
    x = mosviz_helper.app
    assert x.get_viewer_reference_names() == ['image-viewer', 'spectrum-2d-viewer',
                                              'spectrum-viewer', 'table-viewer']
    assert x.get_viewer_ids() == ['mosviz-0', 'mosviz-1', 'mosviz-2', 'mosviz-3']


def test_default_viewer_ids_specviz(specviz_helper, spectrum1d):
    x = specviz_helper.app
    assert x.get_viewer_reference_names() == []

    specviz_helper.load(spectrum1d)
    assert x.get_viewer_reference_names() == ['1D Spectrum']
    assert x.get_viewer_ids() == ['1D Spectrum']


def test_default_viewer_ids_specviz2d(specviz2d_helper, mos_spectrum2d):
    x = specviz2d_helper.app
    assert x.get_viewer_reference_names() == []

    specviz2d_helper.load(mos_spectrum2d, format='2D Spectrum')
    assert x.get_viewer_reference_names() == ['2D Spectrum', '1D Spectrum']
    assert x.get_viewer_ids() == ['2D Spectrum', '1D Spectrum']
