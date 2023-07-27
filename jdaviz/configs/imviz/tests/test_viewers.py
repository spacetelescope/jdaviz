import numpy as np
import pytest
from regions import CirclePixelRegion, PixCoord

from jdaviz.app import Application
from jdaviz.core.config import get_configuration
from jdaviz.configs.imviz.helper import Imviz
from jdaviz.configs.imviz.plugins.viewers import ImvizImageView


@pytest.mark.parametrize(
    ('desired_name', 'actual_name'),
    [(None, 'imviz-1'),
     ('babylon-5', 'babylon-5')])
def test_create_destroy_viewer(imviz_helper, desired_name, actual_name):
    assert imviz_helper.app.get_viewer_ids() == ['imviz-0']

    viewer = imviz_helper.create_image_viewer(viewer_name=desired_name)
    viewer_names = sorted(['imviz-0', actual_name])
    assert viewer.top_visible_data_label == ''
    assert isinstance(viewer, ImvizImageView)
    assert viewer is imviz_helper.app._viewer_store.get(actual_name), list(imviz_helper.app._viewer_store.keys())  # noqa
    assert imviz_helper.app.get_viewer_ids() == viewer_names

    # Make sure plugins that store viewer_items are updated.
    assert sorted(imviz_helper.plugins['Compass'].viewer.labels) == viewer_names

    imviz_helper.destroy_viewer(actual_name)
    assert imviz_helper.app.get_viewer_ids() == ['imviz-0']


def test_get_viewer_created(imviz_helper):
    # This viewer has no reference but has ID.
    viewer1 = imviz_helper.create_image_viewer()
    viewer2 = imviz_helper.app.get_viewer('imviz-1')
    assert viewer1 is viewer2


def test_destroy_viewer_invalid(imviz_helper):
    assert imviz_helper.app.get_viewer_ids() == ['imviz-0']

    imviz_helper.destroy_viewer('foo')
    assert imviz_helper.app.get_viewer_ids() == ['imviz-0']

    with pytest.raises(ValueError, match='cannot be destroyed'):
        imviz_helper.destroy_viewer('imviz-0')
    assert imviz_helper.app.get_viewer_ids() == ['imviz-0']


def test_destroy_viewer_with_subset(imviz_helper):
    """Regression test for https://github.com/spacetelescope/jdaviz/issues/1614"""
    arr = np.ones((10, 10))
    imviz_helper.load_data(arr, data_label='my_array')

    # Create a second viewer.
    imviz_helper.create_image_viewer(viewer_name='second')

    # Add existing data to second viewer.
    imviz_helper.app.add_data_to_viewer('second', 'my_array')

    # Create a Subset.
    reg = CirclePixelRegion(center=PixCoord(x=4, y=4), radius=2)
    imviz_helper.load_regions(reg)

    # Remove the second viewer.
    imviz_helper.destroy_viewer('second')

    # Delete the Subset: Should have no traceback.
    imviz_helper._delete_region('Subset 1')


def test_mastviz_config():
    """Use case from https://github.com/spacetelescope/jdaviz/issues/1037"""

    # create a MAST config dict
    cc = get_configuration('imviz')
    cc['settings']['viewer_spec'] = cc['settings'].get('configuration', 'default')
    cc['settings']['configuration'] = 'mastviz'
    cc['settings']['visible'] = {'menu_bar': False, 'toolbar': False, 'tray': False,
                                 'tab_headers': False}
    cc['toolbar'].remove('g-data-tools') if cc['toolbar'].count('g-data-tools') else None
    cc['toolbar'].remove('g-viewer-creator') if cc['toolbar'].count('g-viewer-creator') else None
    cc['toolbar'].remove('g-image-viewer-creator') if cc['toolbar'].count('g-image-viewer-creator') else None  # noqa

    app = Application(cc)
    im = Imviz(app)
    im.load_data(np.ones((2, 2)), data_label='my_array')

    assert im.app.get_viewer_ids() == ['mastviz-0']
    assert im.app.data_collection[0].shape == (2, 2)
