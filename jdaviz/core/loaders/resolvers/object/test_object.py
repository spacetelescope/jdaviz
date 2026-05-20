from jdaviz.core.loaders.resolvers.object.object import ObjectResolver


def test_object_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test _check_is_valid for ObjectResolver: success and failure cases."""
    resolver = ObjectResolver(app=deconfigged_helper._app)

    # Success: plain Python object (not a path, URI, or Path)
    resolver._object = {'key': 'value'}
    assert resolver._check_is_valid() == ''

    # Failure: existing file path string
    filepath = tmp_path / 'test.fits'
    filepath.write_text('data')
    resolver._object = str(filepath)
    assert resolver._check_is_valid() == 'Object is a file path.'

    # Failure: URI strings
    for uri in ('http://example.com/data.fits', 'https://x.com/d.fits',
                'ftp://x.com/d.fits', 's3://bucket/data.fits',
                'mast://example/data.fits'):
        resolver._object = uri
        assert resolver._check_is_valid() == 'Object is an uri.'

    # Failure: Path objects
    resolver._object = filepath
    assert resolver._check_is_valid() == 'Path objects should be treated as files.'
