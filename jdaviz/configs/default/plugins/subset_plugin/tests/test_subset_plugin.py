import pytest
from glue.core.roi import XRangeROI
from jdaviz.configs.default.plugins import SubsetPlugin


@pytest.mark.filterwarnings('ignore')
def test_plugin(specviz_helper, spectrum1d):
    specviz_helper.load_spectrum(spectrum1d)
    p = specviz_helper.app._subset_tools_plugin

    # regression test for https://github.com/spacetelescope/jdaviz/issues/1693
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    sv.apply_roi(XRangeROI(6500, 7400))

    p.subset_select.selected = 'Create New'

    po = specviz_helper.plugins['Plot Options']
    po.layer = 'Subset 1'
    po.line_color = 'green'
