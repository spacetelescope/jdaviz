from jdaviz.core.loaders.resolvers.url.url import URLResolver


def test_url_resolver_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in URLResolver._check_is_valid."""

    resolver = URLResolver(app=deconfigged_helper._app)

    # Invalid URI scheme
    resolver.url = 'foo://example.com/data.fits'
    resolver.url_scheme = 'foo'
    assert 'URI scheme must be one of' in resolver._check_is_valid()

    # URI not whitelisted
    resolver.url = 'http://not-a-real-whitelisted-domain.example.com/data.fits'
    resolver.url_scheme = 'http'
    resolver.url_not_whitelisted = True
    assert resolver._check_is_valid() == 'URI is not whitelisted.'
