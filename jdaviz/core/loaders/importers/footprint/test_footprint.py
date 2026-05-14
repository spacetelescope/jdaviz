import astropy.units as u
from astropy.coordinates import SkyCoord
from regions import CirclePixelRegion, CircleSkyRegion, PixCoord, Regions

from jdaviz.core.loaders.importers.footprint.footprint import FootprintImporter


def test_footprint_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in FootprintImporter._check_is_valid."""

    def _create_importer(input_data=None):
        return FootprintImporter(app=deconfigged_helper._app,
                                 resolver=None, parser=None,
                                 input=input_data)

    # Non-Region input should be rejected
    importer = _create_importer(input_data='not_a_region')
    assert importer._check_is_valid() == 'Input must be a Region or Regions object.'

    # Pixel regions should be rejected
    pixel_region = Regions([CirclePixelRegion(center=PixCoord(10, 20), radius=5)])
    importer = _create_importer(input_data=pixel_region)
    assert importer._check_is_valid() == 'Input regions must be sky regions.'

    # When Footprint plugin is not available, should be rejected
    sky_region = Regions([CircleSkyRegion(
        center=SkyCoord(10, 20, unit='deg'), radius=1 * u.deg)])
    importer = _create_importer(input_data=sky_region)
    assert importer._check_is_valid() == 'Footprint plugin is not available.'
