import pytest

from jdaviz.configs.imviz.plugins.reproject.reproject import HAS_REPROJECT
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_GWCS


@pytest.mark.skipif(not HAS_REPROJECT, reason='reproject not installed')
class TestReproject_WCS_GWCS(BaseImviz_WCS_GWCS):
    def test_reproject_fits_wcs(self):
        self.imviz.link_data(link_type='wcs', error_on_fail=True)

        plg = self.imviz.plugins["Reproject"]
        assert not plg._obj.disabled_msg

        # Attempt to reproject without WCS should be silent no-op.
        plg._obj.dataset_selected = "no_wcs"
        plg._obj.vue_do_reproject()
        assert self.imviz.app.data_collection.labels == ['fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs']

        # Reproject FITS WCS. We do not test the actual reprojection algorithm.
        plg._obj.dataset_selected = 'fits_wcs[DATA]'
        plg._obj.vue_do_reproject()
        assert self.imviz.app.data_collection.labels == ['fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs',
                                                         'Reprojected']
        assert self.imviz.app.data_collection['Reprojected'].meta['orig_label'] == 'fits_wcs[DATA]'
        # Original data should not be loaded in the viewer anymore.
        assert [data.label for data in self.viewer.data()] == ['gwcs[DATA]', 'no_wcs',
                                                               'Reprojected']
        # Reprojected data now is the viewer reference.
        assert self.viewer.state.reference_data.label == 'Reprojected'

        # Reproject again using existing label is not allowed.
        # Only snackbar message is shown, so that is not tested here. Result should be unchanged.
        plg._obj.dataset_selected = 'gwcs[DATA]'
        plg._obj.vue_do_reproject()
        assert self.imviz.app.data_collection.labels == ['fits_wcs[DATA]', 'gwcs[DATA]', 'no_wcs',
                                                         'Reprojected']
        assert self.imviz.app.data_collection['Reprojected'].meta['orig_label'] == 'fits_wcs[DATA]'


@pytest.mark.skipif(not HAS_REPROJECT, reason='reproject not installed')
def test_reproject_no_data(imviz_helper):
    """This should be silent no-op."""
    plg = imviz_helper.plugins["Reproject"]
    plg._obj.vue_do_reproject()
    assert len(imviz_helper.app.data_collection) == 0


@pytest.mark.skipif(HAS_REPROJECT, reason='reproject is installed')
def test_reproject_no_reproject(imviz_helper):
    plg = imviz_helper.plugins["Reproject"]
    assert "Please install reproject" in plg._obj.disabled_msg
