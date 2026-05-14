from jdaviz.core.loaders.parsers.object.object import ObjectParser


def test_object_parser_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in ObjectParser._check_is_valid."""
    parser = ObjectParser(deconfigged_helper._app, None)
    assert parser._check_is_valid() == 'Input must not be None.'
