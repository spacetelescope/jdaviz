from jdaviz.core.loaders.resolvers.file.file import FileResolver


def test_file_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test _check_is_valid for FileResolver: success and failure cases."""
    resolver = FileResolver(app=deconfigged_helper._app)

    # Success: existing file
    real_file = tmp_path / 'real.fits'
    real_file.write_text('data')
    resolver.filepath = str(real_file)
    assert resolver._check_is_valid() == ''

    # Failure: nonexistent file path
    resolver.filepath = str(tmp_path / 'nonexistent.fits')
    assert resolver._check_is_valid() == 'Filepath does not exist.'

    # Failure: directory instead of file
    resolver.filepath = str(tmp_path)
    assert resolver._check_is_valid() == 'Filepath is not a file.'
