import pytest

from jdaviz.configs.imviz.plugins.viewers import ImvizImageView


@pytest.mark.parametrize(
    ('desired_name', 'actual_name'),
    [(None, 'imviz-1'),
     ('babylon-5', 'babylon-5')])
def test_create_destroy_viewer(imviz_app, desired_name, actual_name):
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    viewer = imviz_app.create_image_viewer(viewer_name=desired_name)
    assert isinstance(viewer, ImvizImageView)
    assert viewer is imviz_app.app._viewer_store.get(actual_name), list(imviz_app.app._viewer_store.keys())  # noqa
    assert imviz_app.app.get_viewer_ids() == sorted(['imviz-0', actual_name])

    imviz_app.destroy_viewer(actual_name)
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']


def test_destroy_viewer_invalid(imviz_app):
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    imviz_app.destroy_viewer('foo')
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']

    with pytest.raises(ValueError, match='cannot be destroyed'):
        imviz_app.destroy_viewer('imviz-0')
    assert imviz_app.app.get_viewer_ids() == ['imviz-0']
