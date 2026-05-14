from pathlib import Path
from jdaviz.core.loaders.resolvers.object.object import ObjectResolver


def test_object_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test all string-returning scenarios in ObjectResolver._check_is_valid."""

    # File path string should be rejected (file must exist)
    resolver = ObjectResolver(app=deconfigged_helper._app)
    filepath = tmp_path / 'test.fits'
    filepath.write_text('data')
    resolver._object = str(filepath)
    assert resolver._check_is_valid() == 'Object is a file path.'

    # URI strings should be rejected
    for uri in ('http://example.com/data.fits', 'https://x.com/d.fits',
                'ftp://x.com/d.fits', 's3://bucket/data.fits',
                'mast://example/data.fits'):
        resolver._object = uri
        assert resolver._check_is_valid() == 'Object is an uri.'

    # Path objects should be rejected
    resolver._object = Path('/tmp/test.fits')
    assert resolver._check_is_valid() == 'Path objects should be treated as files.'
