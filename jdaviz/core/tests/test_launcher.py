"""
Test the launcher module functionality.
"""
import os
from unittest.mock import Mock, patch

import pytest
from astropy.io.registry import IORegistryError
from astropy.nddata import CCDData
import numpy as np

from jdaviz.cli import (
    DEFAULT_VERBOSITY,
    DEFAULT_HISTORY_VERBOSITY,
    ALL_JDAVIZ_CONFIGS
)
from jdaviz.core.launcher import (
    open as jdaviz_open,
    _launch_config_with_data,
    Launcher,
    show_launcher,
    STATUS_HINTS
)


class TestOpenFunction:
    """
    Test the open() function for automatic config detection and
    launching.
    """

    @pytest.mark.filterwarnings('ignore:Jupyter is migrating')
    def test_open_with_local_path_kwarg(self, tmp_path, image_2d_wcs):
        """
        Test open() with local_path kwarg passed through to
        download_uri_to_path.
        """
        # Create a simple FITS file
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.download_uri_to_path'
        ) as mock_download:
            mock_download.return_value = str(test_file)
            with patch(
                'jdaviz.core.launcher.identify_helper'
            ) as mock_identify:
                mock_identify.return_value = (['imviz'], ccd)

                _ = jdaviz_open(
                    str(test_file),
                    show=False,
                    local_path='/some/path'
                )

                mock_download.assert_called_once_with(
                    str(test_file),
                    cache=True,
                    local_path='/some/path'
                )

    @pytest.mark.filterwarnings('ignore:Jupyter is migrating')
    def test_open_without_local_path(self, tmp_path, image_2d_wcs):
        """
        Test open() without local_path kwarg.
        """
        # Create a simple FITS file
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.download_uri_to_path'
        ) as mock_download:
            mock_download.return_value = str(test_file)
            with patch(
                'jdaviz.core.launcher.identify_helper'
            ) as mock_identify:
                mock_identify.return_value = (['imviz'], ccd)

                _ = jdaviz_open(str(test_file), show=False)

                mock_download.assert_called_once_with(
                    str(test_file),
                    cache=True
                )

    def test_open_multiple_helpers_raises_error(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test that open() raises NotImplementedError when multiple
        compatible helpers are identified.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.download_uri_to_path'
        ) as mock_download:
            mock_download.return_value = str(test_file)
            with patch(
                'jdaviz.core.launcher.identify_helper'
            ) as mock_identify:
                mock_identify.return_value = (
                    ['imviz', 'cubeviz'],
                    ccd
                )

                msg = 'Multiple helpers provided'
                with pytest.raises(NotImplementedError, match=msg):
                    jdaviz_open(str(test_file), show=False)

    def test_open_calls_launch_with_correct_params(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test that open() correctly calls _launch_config_with_data with
        the identified helper and data.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.download_uri_to_path'
        ) as mock_download:
            mock_download.return_value = str(test_file)
            with patch(
                'jdaviz.core.launcher.identify_helper'
            ) as mock_identify:
                mock_identify.return_value = (['imviz'], ccd)
                with patch(
                    'jdaviz.core.launcher._launch_config_with_data'
                ) as mock_launch:
                    mock_helper = Mock()
                    mock_launch.return_value = mock_helper

                    result = jdaviz_open(
                        str(test_file),
                        show=False,
                        data_label='my_data'
                    )

                    mock_launch.assert_called_once_with(
                        'imviz',
                        ccd,
                        filepath=str(test_file),
                        show=False,
                        data_label='my_data'
                    )
                    assert result == mock_helper


class TestLaunchConfigWithData:
    """
    Test the _launch_config_with_data() function.
    """

    def test_launch_config_basic(self, imviz_helper):
        """
        Test basic launching of a config without data.
        """
        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=imviz_helper)

            result = _launch_config_with_data('imviz', show=False)

            mock_configs.Imviz.assert_called_once_with(
                verbosity=DEFAULT_VERBOSITY,
                history_verbosity=DEFAULT_HISTORY_VERBOSITY
            )
            assert result == imviz_helper

    def test_launch_config_with_verbosity(self, imviz_helper):
        """
        Test launching config with custom verbosity settings.
        """
        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=imviz_helper)

            _ = _launch_config_with_data(
                'imviz',
                show=False,
                verbosity='debug',
                history_verbosity='info'
            )

            mock_configs.Imviz.assert_called_once_with(
                verbosity='debug',
                history_verbosity='info'
            )

    def test_launch_config_with_data_loads_successfully(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test launching config with data that loads successfully.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        mock_helper = Mock()
        mock_helper.load_data = Mock()
        mock_helper.show = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            result = _launch_config_with_data(
                'imviz',
                data=ccd,
                show=False,
                data_label='test'
            )

            mock_helper.load_data.assert_called_once_with(
                ccd,
                data_label='test'
            )
            mock_helper.show.assert_not_called()
            assert result == mock_helper

    def test_launch_config_with_data_io_error_uses_filepath(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test that when loading data raises IORegistryError, the
        filepath fallback is used.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        mock_helper = Mock()
        mock_helper.load_data = Mock(
            side_effect=[IORegistryError('Failed'), None]
        )
        mock_helper.show = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            _ = _launch_config_with_data(
                'imviz',
                data=ccd,
                filepath=str(test_file),
                show=False
            )

            assert mock_helper.load_data.call_count == 2
            mock_helper.load_data.assert_any_call(ccd)
            mock_helper.load_data.assert_any_call(str(test_file))

    def test_launch_config_with_data_io_error_no_filepath_raises(self):
        """
        Test that IORegistryError is raised when no filepath fallback
        is provided.
        """
        mock_helper = Mock()
        mock_helper.load_data = Mock(
            side_effect=IORegistryError('Failed')
        )

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            with pytest.raises(IORegistryError, match='Failed'):
                _launch_config_with_data(
                    'imviz',
                    data='some_data',
                    show=False
                )

    def test_launch_config_with_empty_string_data(self):
        """
        Test that empty string data is treated as no data.
        """
        mock_helper = Mock()
        mock_helper.load_data = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            _ = _launch_config_with_data('imviz', data='', show=False)

            mock_helper.load_data.assert_not_called()

    def test_launch_config_with_none_data(self):
        """
        Test that None data is treated as no data.
        """
        mock_helper = Mock()
        mock_helper.load_data = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            _ = _launch_config_with_data(
                'imviz',
                data=None,
                show=False
            )

            mock_helper.load_data.assert_not_called()

    def test_launch_config_with_show_true(self):
        """
        Test that show() is called when show=True.
        """
        mock_helper = Mock()
        mock_helper.show = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            _ = _launch_config_with_data('imviz', show=True)

            mock_helper.show.assert_called_once()


class TestLauncherClass:
    """
    Test the Launcher class.
    """

    def test_launcher_init_default(self):
        """
        Test Launcher initialization with default parameters.
        """
        launcher = Launcher()

        assert launcher.configs == ALL_JDAVIZ_CONFIGS
        assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
        assert launcher.filepath == ''
        assert launcher.loaded_data is None
        assert launcher.hint == STATUS_HINTS['idle']
        assert launcher.file_chooser_visible is False
        assert launcher.valid_path is True
        assert 'cubeviz' in launcher.config_icons
        assert 'specviz' in launcher.config_icons
        assert 'imviz' in launcher.config_icons

    def test_launcher_init_with_custom_configs(self):
        """
        Test Launcher initialization with custom config list.
        """
        custom_configs = ['imviz', 'specviz']
        launcher = Launcher(configs=custom_configs)

        assert launcher.configs == custom_configs
        assert launcher.compatible_configs == custom_configs

    def test_launcher_init_with_filepath(self, tmp_path, image_2d_wcs):
        """
        Test Launcher initialization with a filepath.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            launcher = Launcher(filepath=str(test_file))

            assert launcher.filepath == str(test_file)
            assert launcher.hint == STATUS_HINTS['id ok']
            assert launcher.compatible_configs == ['imviz']

    def test_launcher_init_with_height_int(self):
        """
        Test Launcher initialization with integer height.
        """
        launcher = Launcher(height=600)

        assert launcher.height == '600px'

    def test_launcher_init_with_height_string(self):
        """
        Test Launcher initialization with string height.
        """
        launcher = Launcher(height='100%')

        assert launcher.height == '100%'

    def test_launcher_init_with_main(self):
        """
        Test Launcher initialization with custom main widget.
        """
        mock_main = Mock()
        launcher = Launcher(main=mock_main)

        assert launcher.main == mock_main

    def test_launcher_vdocs_with_dev_version(self):
        """
        Test that vdocs is set to 'latest' for dev versions.
        """
        with patch('jdaviz.core.launcher.__version__', '1.0.dev'):
            launcher = Launcher()
            assert launcher.vdocs == 'latest'

    def test_launcher_vdocs_with_release_version(self):
        """
        Test that vdocs is set to versioned string for releases.
        """
        with patch('jdaviz.core.launcher.__version__', '1.2.3'):
            launcher = Launcher()
            assert launcher.vdocs == 'v1.2.3'

    def test_launcher_jdaviz_start_dir_env_var(self):
        """
        Test that JDAVIZ_START_DIR environment variable is respected.
        """
        test_dir = '/custom/start/dir'
        with patch.dict(os.environ, {'JDAVIZ_START_DIR': test_dir}):
            with patch(
                'jdaviz.core.launcher.FileChooser'
            ) as mock_fc:
                _ = Launcher()
                mock_fc.assert_called_once_with(test_dir)

    def test_filepath_changed_to_empty_string(self):
        """
        Test that setting filepath to empty string resets to idle
        state.
        """
        launcher = Launcher()
        launcher.filepath = 'something'
        launcher.filepath = ''

        assert launcher.hint == STATUS_HINTS['idle']
        assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
        assert launcher.loaded_data is None

    def test_filepath_changed_to_invalid_path(self):
        """
        Test that setting filepath to invalid path shows error.
        """
        launcher = Launcher()
        launcher.filepath = '/this/path/does/not/exist.fits'

        assert launcher.hint == STATUS_HINTS['invalid path']
        assert launcher.compatible_configs == []
        assert launcher.loaded_data is None

    def test_filepath_changed_to_valid_file(self, tmp_path, image_2d_wcs):
        """
        Test that setting filepath to valid file identifies configs.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            launcher = Launcher()
            launcher.filepath = str(test_file)

            assert launcher.hint == STATUS_HINTS['id ok']
            assert launcher.compatible_configs == ['imviz']
            assert launcher.loaded_data == ccd

    def test_filepath_changed_identify_fails(self, tmp_path, image_2d_wcs):
        """
        Test that identification failure shows all configs and uses
        filepath as data.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.side_effect = Exception('Identification failed')

            launcher = Launcher()
            launcher.filepath = str(test_file)

            assert launcher.hint == STATUS_HINTS['id failed']
            assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
            assert launcher.loaded_data == str(test_file)

    def test_filepath_changed_identify_returns_empty_list(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test behavior when identify_helper returns empty config list
        with None data - should leave loaded_data as None.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = ([], None)

            launcher = Launcher()
            launcher.filepath = str(test_file)

            # When configs is empty but data is None, loaded_data stays None
            assert launcher.loaded_data is None
            assert launcher.compatible_configs == []

    def test_vue_choose_file_no_file_selected(self):
        """
        Test vue_choose_file when no file is selected.
        """
        launcher = Launcher()
        launcher._file_chooser.file_path = None

        launcher.vue_choose_file()

        assert launcher.error_message == 'No file selected'

    def test_vue_choose_file_with_valid_file(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test vue_choose_file with a valid file selection.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            launcher = Launcher()
            launcher._file_chooser.file_path = str(test_file)

            launcher.vue_choose_file()

            assert launcher.file_chooser_visible is False
            assert launcher.filepath == str(test_file)

    def test_vue_choose_file_with_directory(self, tmp_path):
        """
        Test vue_choose_file when a directory is selected (should not
        update filepath).
        """
        launcher = Launcher()
        launcher._file_chooser.file_path = str(tmp_path)
        launcher.file_chooser_visible = True

        launcher.vue_choose_file()

        # Should not change filepath or visibility since path is not a file
        assert launcher.file_chooser_visible is True
        assert launcher.filepath == ''

    def test_vue_launch_config(self, tmp_path, image_2d_wcs):
        """
        Test vue_launch_config method.
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        mock_helper = Mock()
        mock_app = Mock()
        mock_helper.app = mock_app
        mock_app.state.settings = {
            'context': {'notebook': {'max_height': '800px'}}
        }
        mock_app.layout = Mock()

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            with patch(
                'jdaviz.core.launcher._launch_config_with_data'
            ) as mock_launch:
                mock_launch.return_value = mock_helper

                # Mock the main widget to avoid trait validation errors
                mock_main = Mock()
                launcher = Launcher(main=mock_main, height=600)
                launcher.filepath = str(test_file)

                event = {'config': 'imviz'}
                launcher.vue_launch_config(event)

                mock_launch.assert_called_once_with(
                    'imviz',
                    ccd,
                    filepath=str(test_file),
                    show=False
                )
                assert launcher.main.color == 'transparent'
                assert launcher.main.children == [mock_app]

    def test_vue_launch_config_with_fullscreen_height(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test vue_launch_config with fullscreen height (100%).
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        mock_helper = Mock()
        mock_app = Mock()
        mock_helper.app = mock_app
        mock_app.layout = Mock()

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            with patch(
                'jdaviz.core.launcher._launch_config_with_data'
            ) as mock_launch:
                mock_launch.return_value = mock_helper

                # Mock the main widget to avoid trait validation errors
                mock_main = Mock()
                launcher = Launcher(main=mock_main, height='100%')
                launcher.filepath = str(test_file)

                event = {'config': 'imviz'}
                launcher.vue_launch_config(event)

                # Verify the helper was launched and main was updated
                mock_launch.assert_called_once()
                assert launcher.main.color == 'transparent'
                assert launcher.main.children == [mock_app]

    def test_vue_launch_config_with_100vh_height(
        self, tmp_path, image_2d_wcs
    ):
        """
        Test vue_launch_config with viewport height (100vh).
        """
        test_file = tmp_path / 'test_image.fits'
        data = np.ones((10, 10))
        ccd = CCDData(data=data, unit='adu', wcs=image_2d_wcs)
        ccd.write(test_file)

        mock_helper = Mock()
        mock_app = Mock()
        mock_helper.app = mock_app
        mock_app.layout = Mock()

        with patch(
            'jdaviz.core.launcher.identify_helper'
        ) as mock_identify:
            mock_identify.return_value = (['imviz'], ccd)

            with patch(
                'jdaviz.core.launcher._launch_config_with_data'
            ) as mock_launch:
                mock_launch.return_value = mock_helper

                # Mock the main widget to avoid trait validation errors
                mock_main = Mock()
                launcher = Launcher(main=mock_main, height='100vh')
                launcher.filepath = str(test_file)

                event = {'config': 'imviz'}
                launcher.vue_launch_config(event)

                # Verify the helper was launched and main was updated
                mock_launch.assert_called_once()
                assert launcher.main.color == 'transparent'
                assert launcher.main.children == [mock_app]

    def test_main_with_launcher_property(self):
        """
        Test main_with_launcher property returns main with launcher as
        child.
        """
        launcher = Launcher()
        result = launcher.main_with_launcher

        assert result == launcher.main
        assert launcher.main.children == [launcher]


class TestShowLauncher:
    """
    Test the show_launcher() function.
    """

    def test_show_launcher_default(self):
        """
        Test show_launcher with default parameters.
        """
        with patch('jdaviz.core.launcher.Launcher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.main_with_launcher = Mock()
            mock_launcher_class.return_value = mock_launcher

            with patch('jdaviz.core.launcher.show_widget') as mock_show:
                show_launcher()

                mock_launcher_class.assert_called_once_with(
                    None,
                    ALL_JDAVIZ_CONFIGS,
                    '',
                    '450px'
                )
                mock_show.assert_called_once_with(
                    mock_launcher.main_with_launcher,
                    loc='inline',
                    title=None
                )

    def test_show_launcher_with_custom_params(self):
        """
        Test show_launcher with custom parameters.
        """
        custom_configs = ['imviz', 'specviz']
        custom_filepath = '/path/to/file.fits'
        custom_height = 800

        with patch('jdaviz.core.launcher.Launcher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.main_with_launcher = Mock()
            mock_launcher_class.return_value = mock_launcher

            with patch('jdaviz.core.launcher.show_widget') as _:
                show_launcher(
                    configs=custom_configs,
                    filepath=custom_filepath,
                    height=custom_height
                )

                mock_launcher_class.assert_called_once_with(
                    None,
                    custom_configs,
                    custom_filepath,
                    '800px'
                )

    def test_show_launcher_with_string_height(self):
        """
        Test show_launcher with string height.
        """
        with patch('jdaviz.core.launcher.Launcher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.main_with_launcher = Mock()
            mock_launcher_class.return_value = mock_launcher

            with patch('jdaviz.core.launcher.show_widget') as _:
                show_launcher(height='100%')

                mock_launcher_class.assert_called_once_with(
                    None,
                    ALL_JDAVIZ_CONFIGS,
                    '',
                    '100%'
                )


class TestStatusHints:
    """
    Test STATUS_HINTS dictionary completeness.
    """

    def test_status_hints_keys(self):
        """
        Test that STATUS_HINTS contains expected keys.
        """
        expected_keys = {
            'idle',
            'identifying',
            'invalid path',
            'id ok',
            'id failed'
        }
        assert set(STATUS_HINTS.keys()) == expected_keys

    def test_status_hints_values_are_strings(self):
        """
        Test that all STATUS_HINTS values are strings.
        """
        for key, value in STATUS_HINTS.items():
            assert isinstance(value, str), \
                f'STATUS_HINTS[{key!r}] is not a string'
