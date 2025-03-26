import pytest
import numpy as np

from glue.core import Data
from jdaviz.app import Application
from jdaviz.configs.mosviz.plugins.slit_overlay.slit_overlay import jwst_header_to_skyregion

from regions import RectangleSkyRegion
from astropy.coordinates import Angle, SkyCoord
from astropy import units as u


header = {'S_REGION': 'POLYGON ICRS  5.029236065 4.992154276 5.029513148 '
          '4.992154276 5.029513148 4.992468585 5.029236065 4.992468585'}

skycoord = SkyCoord(5.02937461, 4.99231143,
                    unit=(u.Unit(u.deg),
                          u.Unit(u.deg)))

sky_region = RectangleSkyRegion(center=skycoord, width=Angle(0.0003143089999999251, u.deg),
                                height=Angle(0.00027603191980735836, u.deg))


@pytest.mark.skip("Test needs to be fixed")
def test_slit_overlay(spectral_cube_wcs):
    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    # so = SlitOverlay(app=app)
    #
    # so_sky_region = so.jwst_header_to_skyregion(header)
    #
    # assert np.allclose(sky_region.width.value, so_sky_region.width.value)
    # assert np.allclose(sky_region.height.value, so_sky_region.height.value)
    # assert sky_region.center.to_string() == so_sky_region.center.to_string()


def test_jwst_header_to_skyregion():
    header = {'S_REGION': 'POLYGON ICRS 10.0 20.0 30.0 40.0 50.0 60.0 70.0 80.0'}
    skyregion = jwst_header_to_skyregion(header)
    height = Angle(26.32660752556319, u.deg)
    center = SkyCoord(40.0, 50.0, unit=u.deg)

    assert skyregion.height == height
    assert skyregion.center == center
