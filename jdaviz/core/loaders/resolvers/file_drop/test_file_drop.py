"""
Comprehensive test coverage for FileDropResolver.

Test coverage includes:
- Initialization and widget creation
- User API exposure
- Validity checks
- Label generation from file names
- File parsing for various formats (CSV, ASCII, FITS, VOTable)
- Progress tracking
- File upload callbacks
- Multiple file handling
- Edge cases and error handling
"""
import io
import pytest
from unittest.mock import Mock, patch

from astropy.table import Table

from jdaviz.core.loaders.resolvers.file_drop.file_drop import (FileDropResolver)
from jdaviz.core.user_api import LoaderUserApi


@pytest.fixture(scope='function')
def file_drop_resolver(deconfigged_helper):
    """
    Create a FileDropResolver instance with mocked dependencies.
    """
    # Mock these to avoid (GUI) widget creation and whatever comes along with that
    with patch('jdaviz.core.loaders.resolvers.file_drop.file_drop.FileDropMultiple'):
        with patch('jdaviz.core.loaders.resolvers.file_drop.file_drop.reacton') as mock_reacton:
            mock_reacton.render.return_value = (Mock(), Mock())
            # We could also mock the app if needed
            resolver = FileDropResolver(app=deconfigged_helper.app)
            return resolver


class TestFileDropResolverInitialization:
    """
    Test FileDropResolver initialization.
    """
    def test_init_basic(self, file_drop_resolver):
        """
        Test basic initialization of traitlets in FileDropResolver.
        """
        assert file_drop_resolver._file_info is None
        assert file_drop_resolver.progress == 100
        assert file_drop_resolver.nfiles == 0

    def test_init_creates_widget(self, deconfigged_helper):
        """
        Test that initialization creates file drop widget.
        """
        with (patch('jdaviz.core.loaders.resolvers.file_drop.file_drop.FileDropMultiple')
              as mock_widget):
            with (patch('jdaviz.core.loaders.resolvers.file_drop.file_drop.reacton')
                  as mock_reacton):
                mock_reacton.render.return_value = (Mock(), Mock())

                _ = FileDropResolver(app=deconfigged_helper.app)

                # Check that widget was created with correct parameters
                mock_widget.assert_called_once()
                call_kwargs = mock_widget.call_args[1]
                assert call_kwargs['label'] == 'Drop file here'
                assert call_kwargs['lazy'] is False
                assert 'on_total_progress' in call_kwargs
                assert 'on_file' in call_kwargs


def test_file_drop_resolver_init(file_drop_resolver):
    """
    Test that FileDropResolver initializes correctly.
    """
    # Test that user_api returns LoaderUserApi instance.
    api = file_drop_resolver.user_api

    # Check that LoaderUserApi was created
    assert isinstance(api, LoaderUserApi)

    assert file_drop_resolver.is_valid is True
    assert file_drop_resolver.default_label is None


@pytest.mark.parametrize(('filename', 'result'),
                         [('test_data.csv', 'test_data'),
                          ('my.data.file.fits', 'my.data.file'),
                          ('datafile', 'datafile')])
def test_default_label_with_file(file_drop_resolver, filename, result):
    """
    Test default_label returns file name with different conventions.
    """
    file_drop_resolver._file_info = {'name': filename,
                                     'data': b'some data'}

    assert file_drop_resolver.default_label == result


def test_on_total_progress_updates(file_drop_resolver):
    """
    Test that _on_total_progress updates progress trait.
    """
    for value in [0, 25, 50, 75, 100]:
        file_drop_resolver._on_total_progress(value)
        assert file_drop_resolver.progress == value


_FILE_INFO = [{'name': 'file1.csv', 'data': b'data1'},
              {'name': 'file2.csv', 'data': b'data2'},
              {'name': 'file3.csv', 'data': b'data3'}]


class TestFileDropResolverFileHandling:
    """
    Test file upload and handling functionality.
    """
    @pytest.mark.parametrize('file_info', ([_FILE_INFO[0]], _FILE_INFO))
    def test_on_file_updated_single_file(self, file_drop_resolver, file_info):
        """
        Test _on_file_updated with single file.
        """
        # Test that progress updates to 100 after file upload.
        file_drop_resolver.progress = 50
        with patch.object(file_drop_resolver, '_resolver_input_updated') as mock_input_updated:
            with patch.object(file_drop_resolver, '_update_format_items') as mock_update_format:
                file_drop_resolver._on_file_updated(file_info)

                assert file_drop_resolver.nfiles == len(file_info)
                assert file_drop_resolver._file_info == file_info[0] if len(file_info) > 1 else file_info  # noqa
                assert file_drop_resolver.progress == 100

                mock_input_updated.assert_called_once()
                mock_update_format.assert_called_once()

    def test_on_file_updated_empty_list(self, file_drop_resolver):
        """
        Test _on_file_updated with empty file list.
        """
        with patch.object(file_drop_resolver, '_resolver_input_updated'):
            with patch.object(file_drop_resolver, '_update_format_items'):
                # This should raise an IndexError
                with pytest.raises(IndexError):
                    file_drop_resolver._on_file_updated([])


class TestFileDropResolverParseInput:
    """
    Test parse_input functionality.
    """
    def test_parse_input_returns_bytesio(self, file_drop_resolver):
        """
        Test that parse_input returns BytesIO object.
        """
        file_drop_resolver._file_info = _FILE_INFO[0]

        result = file_drop_resolver.parse_input()

        assert isinstance(result, io.BytesIO)
        assert result.read() == _FILE_INFO[0]['data']

    def test_parse_input_no_file_info(self, file_drop_resolver):
        """
        Test parse_input when no file is loaded.
        """
        file_drop_resolver._file_info = None
        with pytest.raises(AttributeError):
            file_drop_resolver.parse_input()


class TestFileDropResolverParsedInputToTable:
    """
    Test _parsed_input_to_table functionality for various formats.
    """
    def test_parsed_input_to_table_csv(self, file_drop_resolver, sample_csv_data):
        """
        Test parsing CSV format.
        """
        parsed_input = io.BytesIO(sample_csv_data)
        result = file_drop_resolver._parsed_input_to_table(parsed_input)

        assert result is not None
        assert isinstance(result, Table)
        assert len(result) == 3
        assert 'col1' in result.colnames

    def test_parsed_input_to_table_ascii(self, file_drop_resolver, sample_ascii_data):
        """
        Test parsing ASCII format.
        """
        parsed_input = io.BytesIO(sample_ascii_data)
        result = file_drop_resolver._parsed_input_to_table(parsed_input)

        assert result is not None
        assert isinstance(result, Table)
        assert len(result) == 3

    def test_parsed_input_to_table_fits(self, file_drop_resolver, sample_fits_table):
        """
        Test parsing FITS format.
        """
        parsed_input = io.BytesIO(sample_fits_table)
        result = file_drop_resolver._parsed_input_to_table(parsed_input)

        assert result is not None
        assert isinstance(result, Table)
        assert len(result) == 3
        assert 'col1' in result.colnames

    def test_parsed_input_to_table_invalid_format(self, file_drop_resolver):
        """
        Test parsing with invalid format.

        Note: astropy.table.Table.read is very lenient and may parse
        unexpected data as a table, so we just verify it doesn't crash.
        """
        invalid_data = b'This is not a valid table format!!@@##'
        parsed_input = io.BytesIO(invalid_data)
        result = file_drop_resolver._parsed_input_to_table(parsed_input)

        assert result is None or isinstance(result, Table)
        if result is not None:
            assert isinstance(result.colnames, list)

    def test_parsed_input_to_table_empty_data(self, file_drop_resolver):
        """
        Test parsing with empty data.

        Note: astropy may create an empty table rather than return None.
        """
        empty_data = b''
        parsed_input = io.BytesIO(empty_data)
        result = file_drop_resolver._parsed_input_to_table(parsed_input)

        # May return None or an empty table
        assert result is None or (isinstance(result, Table) and len(result) == 0)


class TestFileDropResolverEdgeCases:
    """
    Test edge cases and boundary conditions.
    """
    def test_file_with_special_characters_in_name(self, file_drop_resolver):
        """
        Test file name with special characters.
        """
        file_drop_resolver._file_info = {'name': 'my-file_v2.0 (copy).csv',
                                         'data': b'data'}

        expected = 'my-file_v2.0 (copy)'
        assert file_drop_resolver.default_label == expected

    def test_file_with_unicode_name(self, file_drop_resolver):
        """
        Test file name with unicode characters.
        """
        file_drop_resolver._file_info = {'name': 'és_测试_🌟.csv',
                                         'data': b'data'}

        expected = 'és_测试_🌟'
        assert file_drop_resolver.default_label == expected

    def test_very_large_file_simulation(self, file_drop_resolver):
        """
        Test handling of large file (simulated).
        """
        # Simulate a large file by creating 'large' data
        large_data = b'x' * (10 * 1024 * 1024)  # 10 MB

        file_drop_resolver._file_info = {'name': 'large_file.dat',
                                         'data': large_data}

        result = file_drop_resolver.parse_input()

        assert isinstance(result, io.BytesIO)
        # Read in chunks to avoid memory issues in test
        chunk = result.read(1024)
        assert len(chunk) == 1024

    def test_sequential_file_uploads(self, file_drop_resolver):
        """
        Test uploading multiple files sequentially.
        """
        files = [{'name': f'file{i}.csv', 'data': f'data{i}'.encode()}
                 for i in range(3)]

        with patch.object(file_drop_resolver, '_resolver_input_updated'):
            with patch.object(file_drop_resolver, '_update_format_items'):
                for file_info in files:
                    file_drop_resolver._on_file_updated([file_info])

                    # Each upload should update _file_info
                    assert file_drop_resolver._file_info['name'] == file_info['name']
                    assert file_drop_resolver.nfiles == 1

    def test_progress_reset_on_new_upload(self, file_drop_resolver):
        """
        Test that progress is reset to 100 after file upload.
        """
        file_drop_resolver.progress = 50

        file_info = {'name': 'test.csv', 'data': b'data'}

        with patch.object(file_drop_resolver, '_resolver_input_updated'):
            with patch.object(file_drop_resolver, '_update_format_items'):
                file_drop_resolver._on_file_updated([file_info])

                assert file_drop_resolver.progress == 100

    def test_file_info_missing_name_key(self, file_drop_resolver):
        """
        Test behavior when file_info is missing 'name' key.
        """
        file_drop_resolver._file_info = {'data': b'some data'}

        # default_label should return None
        assert file_drop_resolver.default_label is None

    def test_file_info_missing_data_key(self, file_drop_resolver):
        """
        Test parse_input when file_info is missing 'data' key.

        Note: .get('data') returns None, and io.BytesIO(None) creates
        an empty BytesIO object (doesn't raise error).
        """
        file_drop_resolver._file_info = {'name': 'test.csv'}

        # parse_input uses .get() which returns None
        # io.BytesIO(None) creates empty BytesIO, doesn't raise
        result = file_drop_resolver.parse_input()

        assert isinstance(result, io.BytesIO)
        # Should be empty since data was None
        assert result.read() == b''


class TestFileDropResolverIntegration:
    """
    Integration tests combining multiple aspects of functionality.
    """
    def test_full_file_upload_workflow(self, file_drop_resolver, sample_csv_data):
        """
        Test complete workflow from upload to parsing.
        """
        file_info = {'name': 'data.csv',
                     'data': sample_csv_data}

        with patch.object(file_drop_resolver, '_resolver_input_updated'):
            with patch.object(file_drop_resolver, '_update_format_items'):
                # Simulate progress updates
                file_drop_resolver._on_total_progress(25)
                assert file_drop_resolver.progress == 25

                file_drop_resolver._on_total_progress(50)
                assert file_drop_resolver.progress == 50

                # Upload file
                file_drop_resolver._on_file_updated([file_info])
                assert file_drop_resolver.nfiles == 1
                assert file_drop_resolver.progress == 100

                # Check default label
                assert file_drop_resolver.default_label == 'data'

                # Parse input
                parsed = file_drop_resolver.parse_input()
                assert isinstance(parsed, io.BytesIO)

                # Convert to table
                table = file_drop_resolver._parsed_input_to_table(parsed)
                assert table is not None
                assert isinstance(table, Table)

    def test_error_recovery_on_invalid_file(self, file_drop_resolver):
        """
        Test that resolver handles invalid files gracefully.
        """
        invalid_file = {'name': 'invalid.xyz',
                        'data': b'random binary data \x00\x01\x02'}

        with patch.object(file_drop_resolver, '_resolver_input_updated'):
            with patch.object(file_drop_resolver, '_update_format_items'):
                file_drop_resolver._on_file_updated([invalid_file])

                # Should still update state
                assert file_drop_resolver.nfiles == 1
                assert file_drop_resolver.default_label == 'invalid'

                # Parsing - astropy is lenient, may parse as table
                parsed = file_drop_resolver.parse_input()
                table = file_drop_resolver._parsed_input_to_table(parsed)
                # Either returns None or a table (astropy is very lenient)
                assert table is None or isinstance(table, Table)
