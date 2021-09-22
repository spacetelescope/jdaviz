import pytest


def test_create_destroy_viewer(imviz_app):
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    imviz_app.create_image_viewer()
    assert imviz_app.app.get_viewer_ids() == ['imviz-0', 'imviz-1']

    imviz_app.destroy_viewer('imviz-1')
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']


def test_destroy_viewer_invalid(imviz_app):
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    imviz_app.destroy_viewer('foo')
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    with pytest.raises(ValueError, match='cannot be destroyed'):
        imviz_app.destroy_viewer('imviz-0')
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']
