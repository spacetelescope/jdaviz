from unittest.mock import patch
import zipfile

import numpy as np
import pytest
from astropy.io import fits

from jdaviz.core.loaders.resolvers.url.url import URLResolver, _unpack_if_archive


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


def test_url_resolver_archive_populates_formats(deconfigged_helper, tmp_path):
    """A downloaded archive is expanded and each member participates in format detection."""
    archive_path = tmp_path / 'images.zip'
    member_paths = []
    for index in range(2):
        member_path = tmp_path / f'image-{index}.fits'
        fits.PrimaryHDU(np.zeros((5, 5))).writeto(member_path)
        member_paths.append(member_path)
    with zipfile.ZipFile(archive_path, 'w') as archive:
        for member_path in member_paths:
            archive.write(member_path, arcname=member_path.name)

    resolver = URLResolver(app=deconfigged_helper._app)
    with patch('jdaviz.core.loaders.resolvers.url.url.download_uri_to_path',
               return_value=str(archive_path)):
        resolver.url = 'https://example.com/images.zip'

    assert len(resolver.output) == 2
    assert 'Image' in resolver.format.choices


def test_url_resolver_rejects_html_download(deconfigged_helper, tmp_path):
    """Landing and authentication pages produce an actionable resolver error."""
    html_path = tmp_path / 'download'
    html_path.write_text('<!DOCTYPE html><html><body>Login</body></html>')

    resolver = URLResolver(app=deconfigged_helper._app)
    with patch('jdaviz.core.loaders.resolvers.url.url.download_uri_to_path',
               return_value=str(html_path)):
        resolver.url = 'https://example.com/shared-page'

    assert resolver.format.choices == []
    assert 'direct download URL' in resolver.parsed_input_not_resolvable_message


@pytest.mark.parametrize('suffix', ['.zip', '.tar'])
def test_unpack_archive(tmp_path, suffix):
    """ZIP and TAR archives return their extracted regular-file members."""
    member_path = tmp_path / 'member.txt'
    member_path.write_text('content')
    archive_path = tmp_path / f'archive{suffix}'

    if suffix == '.zip':
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.write(member_path, arcname=member_path.name)
    else:
        import tarfile
        with tarfile.open(archive_path, 'w') as archive:
            archive.add(member_path, arcname=member_path.name)

    extracted = _unpack_if_archive(archive_path)
    assert len(extracted) == 1
    assert open(extracted[0]).read() == 'content'
