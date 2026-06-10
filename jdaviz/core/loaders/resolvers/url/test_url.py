import pytest

from jdaviz.core.loaders.resolvers.url.url import URLResolver


# Ignore more strict 404 handling in python 3.14 for now
@pytest.mark.filterwarnings('ignore::pytest.PytestUnraisableExceptionWarning')
def test_url_resolver_is_valid(deconfigged_helper):
    """Test _check_is_valid for URLResolver: success and failure cases."""
    resolver = URLResolver(app=deconfigged_helper._app)

    # Success: valid scheme, not whitelisted restricted
    resolver.url = 'https://mast.stsci.edu/data.fits'
    resolver.url_scheme = 'https'
    resolver.url_not_whitelisted = False
    assert resolver._check_is_valid() == ''

    # Failure: invalid URI scheme
    resolver.url = 'foo://example.com/data.fits'
    resolver.url_scheme = 'foo'
    assert 'URI scheme must be one of' in resolver._check_is_valid()

    # Failure: URI not whitelisted
    resolver.url = 'http://not-a-real-whitelisted-domain.example.com/data.fits'
    resolver.url_scheme = 'http'
    resolver.url_not_whitelisted = True
    assert resolver._check_is_valid() == 'URI is not whitelisted.'
