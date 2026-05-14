from jdaviz.core.loaders.resolvers.file.file import FileResolver


def test_file_resolver_is_valid(deconfigged_helper, tmp_path):
    """Test all string-returning scenarios in FileResolver._check_is_valid."""

    resolver = FileResolver(app=deconfigged_helper._app)

    # Nonexistent file path
    resolver.filepath = str(tmp_path / 'nonexistent.fits')
    assert resolver._check_is_valid() == 'Filepath does not exist.'

    # Directory instead of file
    resolver.filepath = str(tmp_path)
    assert resolver._check_is_valid() == 'Filepath is not a file.'
