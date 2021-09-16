from jdaviz import Application


def test_default_viewer_ids_default():
    app = Application(configuration='default')
    assert app.get_viewer_reference_names() == []
    assert app.get_viewer_ids() == []


# NOTE: Unable to parametrize fixture as input.

def test_default_viewer_ids_cubeviz(cubeviz_app):
    x = cubeviz_app.app
    assert x.get_viewer_reference_names() == ['flux-viewer', 'uncert-viewer', 'mask-viewer',
                                              'spectrum-viewer']
    assert x.get_viewer_ids() == ['cubeviz-0', 'cubeviz-1', 'cubeviz-2', 'cubeviz-3']


def test_default_viewer_ids_imviz(imviz_app):
    x = imviz_app.app
    assert x.get_viewer_reference_names() == ['imviz-0']
    assert x.get_viewer_ids() == ['imviz-0']
    assert x.get_viewer_ids(prefix='imviz') == ['imviz-0']
    assert x.get_viewer_ids(prefix='specviz') == []

    viewer = x.get_viewer('imviz-0')
    assert x.get_viewer_by_id('imviz-0') is viewer


def test_default_viewer_ids_mosviz(mosviz_app):
    x = mosviz_app.app
    assert x.get_viewer_reference_names() == ['image-viewer', 'spectrum-2d-viewer',
                                              'spectrum-viewer', 'table-viewer']
    assert x.get_viewer_ids() == ['mosviz-0', 'mosviz-1', 'mosviz-2', 'mosviz-3']


def test_default_viewer_ids_specviz(specviz_app):
    x = specviz_app.app
    assert x.get_viewer_reference_names() == ['spectrum-viewer']
    assert x.get_viewer_ids() == ['specviz-0']


def test_default_viewer_ids_specviz2d(specviz2d_app):
    x = specviz2d_app.app
    assert x.get_viewer_reference_names() == ['spectrum-2d-viewer', 'spectrum-viewer']
    assert x.get_viewer_ids() == ['specviz2d-0', 'specviz2d-1']
