import pytest
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
from astropy.tests.helper import assert_quantity_allclose


def assert_coordinate_close(coord1, coord2, atol=1 * u.arcsec):
    # check that two coordinates are within some separation tolerance
    separation = coord1.separation(coord2)
    assert_quantity_allclose(separation, desired=0*u.arcsec, atol=atol)


def assert_angle_close(angle1, angle2, atol=1 * u.arcsec):
    # check that two angles are within some separation tolerance
    difference = abs(angle1 - angle2)
    assert_quantity_allclose(difference, desired=0*u.arcsec, atol=atol)


def test_get_viewport_sky(imviz_helper, image_hdu_wcs):
    imviz_helper.load_data(image_hdu_wcs)
    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    viewer = imviz_helper.app.get_viewer('imviz-0')
    viewport = viewer.aid.get_viewport('sky')

    expected_center = SkyCoord(ra=337.51894337, dec=-20.83208305, unit='deg')
    expected_fov = 0.00277778 * u.deg
    expected_image_label = imviz_helper.app.data_collection[0].label

    # by default, the viewer y-axis is the narrower axis, which is used to
    # define the FOV parameter. Use the WCS to find what the actual
    # viewport dimensions are in the x-axis, which maps onto RA in this case:
    wcs = WCS(image_hdu_wcs.header)
    dec_unit = u.Unit(wcs.wcs.cunit[1])
    delta_dec = abs(wcs.wcs.cdelt[1]) * dec_unit
    expected_fov = (
        abs(viewer.state.y_max - viewer.state.y_min) * delta_dec
    )
    assert_coordinate_close(viewport['center'], expected_center)
    assert_angle_close(viewport['fov'], expected_fov)

    assert viewport['image_label'] == expected_image_label


def test_set_viewport_sky(imviz_helper, image_hdu_wcs):
    imviz_helper.load_data(image_hdu_wcs)
    imviz_helper.plugins['Orientation'].align_by = 'WCS'
    viewer = imviz_helper.app.get_viewer('imviz-0')

    # change only the center:
    new_viewport_settings = dict(
        center=SkyCoord(ra=337.5, dec=-20.8, unit='deg'),
        fov=0.01 * u.deg
    )
    viewer.aid.set_viewport(**new_viewport_settings)
    new_viewport = viewer.aid.get_viewport('sky')

    assert_coordinate_close(new_viewport['center'], new_viewport_settings['center'])

    # todo: investigate why this tolerance needs to be larger than expected:
    assert_angle_close(new_viewport['fov'], new_viewport_settings['fov'], atol=1 * u.arcsec)

    with pytest.raises(ValueError, match='The AID API supports `center` arguments as'):
        viewer.aid.set_viewport(center=u.Quantity([0, 1]))


def test_set_viewport_pixel(imviz_helper, image_hdu_wcs):
    imviz_helper.load_data(image_hdu_wcs)

    viewer = imviz_helper.app.get_viewer('imviz-0')

    # change only the center:
    new_viewport_settings = dict(
        center=[5, 5],
        fov=10
    )
    viewer.aid.set_viewport(**new_viewport_settings)
    new_viewport = viewer.aid.get_viewport('pixel')

    np.testing.assert_allclose(new_viewport['center'], new_viewport_settings['center'])

    # todo: investigate why this tolerance needs to be larger than expected:
    np.testing.assert_allclose(new_viewport['fov'], new_viewport_settings['fov'], atol=1e-4)
