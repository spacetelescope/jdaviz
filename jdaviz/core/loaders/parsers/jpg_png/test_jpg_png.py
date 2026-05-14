from jdaviz.core.loaders.parsers.jpg_png.jpg_png import JPGPNGParser


def test_jpgpng_parser_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in JPGPNGParser._check_is_valid."""
    for inp in (12345, 'image.fits', 'image.tiff'):
        parser = JPGPNGParser(deconfigged_helper._app, inp)
        assert parser._check_is_valid() == ('Input must be a string path ending in '
                                            '.jpg, .jpeg, or .png.')
