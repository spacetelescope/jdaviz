from jdaviz.core.loaders.parsers.object.object import ObjectParser


def test_object_parser_is_valid(deconfigged_helper):
    """Test _check_is_valid for ObjectParser: success and failure cases."""
    # Success: any non-None input
    parser = ObjectParser(deconfigged_helper._app, 'some_object')
    assert parser._check_is_valid() == ''

    # Failure: None input
    parser = ObjectParser(deconfigged_helper._app, None)
    assert parser._check_is_valid() == 'Input must not be None.'
