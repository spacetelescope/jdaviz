import pytest
import numpy as np

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


class TestImvizRotateCanvas(BaseImviz_WCS_NoWCS):
    def test_rotate_canvas(self):
        rc = self.imviz.plugins['Canvas Rotation']

        # reference data has WCS
        assert rc._obj.has_wcs is True
        rc.angle = 10
        rc.flip_horizontal = True

        rc.set_north_up_east_left()
        assert np.allclose(rc.angle, -0.0005285079750789092)
        assert rc.flip_horizontal is False

        rc.set_north_up_east_right()
        assert np.allclose(rc.angle, -0.0005285079750789092)
        assert rc.flip_horizontal is True

        rc.reset()
        assert np.allclose(rc.angle, 0.0)
        assert rc.flip_horizontal is False

        # removing WCS data should disable orientation options
        self.imviz.app.remove_data_from_viewer('imviz-0', 'has_wcs[SCI,1]')
        assert rc._obj.has_wcs is False

        with pytest.raises(ValueError,
                           match="reference data does not have WCS, cannot determine orientation"):
            rc.set_north_up_east_left()
