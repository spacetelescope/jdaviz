import warnings
import pytest

from glue.core.roi import XRangeROI


@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    p = specviz_helper.plugins['Subset Tools']

    # regression test for https://github.com/spacetelescope/jdaviz/issues/1693
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    sv.apply_roi(XRangeROI(6500, 7400))

    p._obj.subset_select.selected = 'Create New'

    po = specviz_helper.plugins['Plot Options']
    po.layer = 'Subset 1'
    po.line_color = 'green'


def test_subset_definition_with_composite_subset(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(spectrum1d_cube)
    cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
