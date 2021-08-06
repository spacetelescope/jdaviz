import numpy as np

from glue.core import Data
from jdaviz import Application

from regions import RectangleSkyRegion
from astropy.coordinates import Angle, SkyCoord
from astropy import units as u

from .. import slit_overlay as so

header = {'S_REGION': 'POLYGON ICRS  5.029236065 4.992154276 5.029513148 '
          '4.992154276 5.029513148 4.992468585 5.029236065 4.992468585'}

skycoord = SkyCoord(5.02937461, 4.99231143,
                    unit=(u.Unit(u.deg),
                          u.Unit(u.deg)))

sky_region = RectangleSkyRegion(center=skycoord, width=Angle(0.0003143089999999251, u.deg),
                                height=Angle(0.00027603191980735836, u.deg))


def test_slit_overlay(mosviz_app, spectrum1d, spectrum2d):
    mosviz_app.load_data(spectrum1d, spectrum2d)

    assert so.SlitOverlay.get_visible(so.SlitOverlay) is True


def test_slit_overlay_no_slit(mosviz_app, spectrum1d, spectrum2d, image):
    print(spectrum2d.meta)
    spectrum2d.meta['INSTRUME'] = "NIRISS"
    print(spectrum2d.meta)

    mosviz_app.load_data(spectrum1d, spectrum2d, image)
    pso = so.SlitOverlay.place_slit_overlay

    pso(so.SlitOverlay)

    assert so.SlitOverlay.get_visible(so.SlitOverlay) is False
