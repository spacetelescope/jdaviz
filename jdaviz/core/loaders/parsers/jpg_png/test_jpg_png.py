from jdaviz.core.loaders.parsers.jpg_png.jpg_png import JPGPNGParser


def test_jpgpng_parser_is_valid(deconfigged_helper):
    """Test _check_is_valid for JPGPNGParser: success and failure cases."""
    # Success: valid jpg/jpeg/png path
    for ext in ('image.jpg', 'photo.jpeg', 'picture.png'):
        parser = JPGPNGParser(deconfigged_helper._app, ext)
        assert parser._check_is_valid() == ''

    # Failure: non-string and wrong extensions
    for inp in (12345, 'image.fits', 'image.tiff'):
        parser = JPGPNGParser(deconfigged_helper._app, inp)
        assert parser._check_is_valid() == ('Input must be a string path ending in '
                                            '.jpg, .jpeg, or .png.')
