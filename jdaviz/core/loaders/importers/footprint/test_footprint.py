import astropy.units as u
from astropy.coordinates import SkyCoord
from regions import CirclePixelRegion, CircleSkyRegion, PixCoord, Regions
from unittest.mock import patch, PropertyMock

from jdaviz.core.loaders.importers.footprint.footprint import FootprintImporter


def test_footprint_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for FootprintImporter: success and failure cases."""

    sky_region = Regions([CircleSkyRegion(
        center=SkyCoord(10, 20, unit='deg'), radius=1 * u.deg)])

    importer = FootprintImporter(app=deconfigged_helper._app,
                                 resolver=None, parser=None,
                                 input=sky_region)

    # Success: sky region with Footprints plugin mocked as available
    # (the Footprints plugin is not exposed in headless test mode)
    with patch.object(type(importer), 'has_default_plugin',
                      new_callable=PropertyMock, return_value=True):
        assert importer._check_is_valid() == ''

    # Failure: non-Region input
    importer._input = 'not_a_region'
    assert importer._check_is_valid() == 'Input must be a Region or Regions object.'

    # Failure: pixel regions rejected
    pixel_region = Regions([CirclePixelRegion(center=PixCoord(10, 20), radius=5)])
    importer._input = pixel_region
    assert importer._check_is_valid() == 'Input regions must be sky regions.'

    # Failure: sky region but no Footprint plugin (deconfigged)
    importer._input = sky_region
    assert importer._check_is_valid() == 'Footprint plugin is not available.'
