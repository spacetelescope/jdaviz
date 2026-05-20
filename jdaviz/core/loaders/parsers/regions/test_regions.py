from jdaviz.core.loaders.parsers.regions.regions import RegionsParser


def test_check_regions_parser_is_valid(deconfigged_helper):
    """Test _check_is_valid for RegionsParser in deconfigged config."""
    # Success: supported extensions for deconfigged config
    for ext in ('file.reg', 'file.fits', 'file.ecsv'):
        parser = RegionsParser(deconfigged_helper._app, ext)
        assert parser._check_is_valid() == ''

    # Failure: non-string input
    parser = RegionsParser(deconfigged_helper._app, 12345)
    assert parser._check_is_valid() == 'Input must be a string path or STCS string.'

    # Failure: unsupported extension
    parser = RegionsParser(deconfigged_helper._app, 'file.csv')
    assert parser._check_is_valid() == 'Unsupported extension .csv for regions.'


def test_check_regions_is_valid_imviz(imviz_helper):
    """Test _check_is_valid for RegionsParser in imviz config."""
    # Success: .reg and .fits are valid in imviz
    for ext in ('file.reg', 'file.fits'):
        parser = RegionsParser(imviz_helper._app, ext)
        assert parser._check_is_valid() == ''

    # Failure: unsupported extension
    parser = RegionsParser(imviz_helper._app, 'file.csv')
    assert parser._check_is_valid() == 'Unsupported extension .csv for imviz regions.'


def test_check_regions_is_valid_specviz(specviz_helper):
    """Test _check_is_valid for RegionsParser in specviz config."""
    # Success: .ecsv is valid in specviz
    parser = RegionsParser(specviz_helper._app, 'file.ecsv')
    assert parser._check_is_valid() == ''

    # Failure: unsupported extension
    parser = RegionsParser(specviz_helper._app, 'file.reg')
    assert parser._check_is_valid() == 'Unsupported extension .reg for specviz regions.'


def test_check_regions_is_valid_specviz2d(specviz2d_helper):
    """Test _check_is_valid for RegionsParser in specviz2d config."""
    # Success: .ecsv is valid in specviz2d
    parser = RegionsParser(specviz2d_helper._app, 'file.ecsv')
    assert parser._check_is_valid() == ''

    # Failure: unsupported extension
    parser = RegionsParser(specviz2d_helper._app, 'file.reg')
    assert parser._check_is_valid() == 'Unsupported extension .reg for specviz2d regions.'
