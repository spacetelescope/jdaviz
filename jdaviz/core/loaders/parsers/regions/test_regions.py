from jdaviz.core.loaders.parsers.regions.regions import RegionsParser


def test_check_regions_parser_is_valid(deconfigged_helper):
    """Test string-returning scenarios in RegionsParser._check_is_valid for deconfigged."""
    # Non-string input
    parser = RegionsParser(deconfigged_helper._app, 12345)
    assert parser._check_is_valid() == 'Input must be a string path or STCS string.'

    # Unsupported extension in default (deconfigged) config
    parser = RegionsParser(deconfigged_helper._app, 'file.csv')
    assert parser._check_is_valid() == 'Unsupported extension .csv for regions.'


def test_check_regions_is_valid_imviz(imviz_helper):
    """Test unsupported extension message for imviz config."""
    parser = RegionsParser(imviz_helper._app, 'file.csv')
    assert parser._check_is_valid() == 'Unsupported extension .csv for imviz regions.'


def test_check_regions_is_valid_specviz(specviz_helper):
    """Test unsupported extension message for specviz config."""
    parser = RegionsParser(specviz_helper._app, 'file.reg')
    assert parser._check_is_valid() == 'Unsupported extension .reg for specviz regions.'


def test_check_regions_is_valid_specviz2d(specviz2d_helper):
    """Test unsupported extension message for specviz2d config."""
    parser = RegionsParser(specviz2d_helper._app, 'file.reg')
    assert parser._check_is_valid() == 'Unsupported extension .reg for specviz2d regions.'

