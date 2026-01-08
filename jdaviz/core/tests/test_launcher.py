"""
Test the launcher module functionality.
"""
from ipywidgets import widgets
import os
import pytest
from unittest.mock import Mock, patch

from astropy.io.registry import IORegistryError
from astropy.nddata import CCDData
from astropy.wcs import WCS
import numpy as np
from pathlib import Path

from jdaviz import Imviz
from jdaviz.cli import (DEFAULT_VERBOSITY,
                        DEFAULT_HISTORY_VERBOSITY,
                        ALL_JDAVIZ_CONFIGS)
from jdaviz.core.launcher import (open as jdaviz_open,
                                  _launch_config_with_data,
                                  Launcher,
                                  show_launcher,
                                  STATUS_HINTS)


@pytest.fixture(scope='module')
def _shared_ccd(tmp_path_factory):
    """
    Create a single FITS file once per module and return the CCD and
    filepath.
    """
    test_dir = tmp_path_factory.mktemp('data')
    test_file = test_dir / 'test_image.fits'
    data = np.ones((10, 10))
    wcs = WCS(naxis=2)
    ccd = CCDData(data=data, unit='adu', wcs=wcs)
    ccd.write(test_file)
    return ccd, str(test_file)


@pytest.fixture(autouse=True, scope='module')
def _module_setup(request, _shared_ccd):
    """
    Module-scoped autouse fixture that attaches the shared CCD and
    filepath to all test classes in the module so tests can use
    ``self.ccd`` and ``self.test_file`` without rewriting the file.
    """
    ccd, test_file = _shared_ccd

    # Attach as class attributes to every Test* class in the module.
    for name in dir(request.module):
        obj = getattr(request.module, name)
        if isinstance(obj, type) and name.startswith('Test'):
            setattr(obj, 'ccd', ccd)
            setattr(obj, 'test_file', test_file)


def test_status_hints_keys():
    """
    Test that STATUS_HINTS contains expected keys.
    """
    expected_keys = {'idle',
                     'identifying',
                     'invalid path',
                     'id ok',
                     'id failed'}
    assert set(STATUS_HINTS.keys()) == expected_keys


class TestOpenFunction:
    """
    Test the open() function for automatic config detection and
    launching.
    """
    @pytest.mark.parametrize('local_path', ['/some/path', None])
    def test_open_with_local_path_kwarg(self, local_path):
        """
        Test open() with local_path kwarg passed through to
        download_uri_to_path and with multiple compatible helpers.
        """
        # Mock the download to avoid actual network calls.
        with (patch('jdaviz.core.launcher.download_uri_to_path') as mock_download):
            mock_download.return_value = self.test_file
            # mock the identify_helper to force imviz to be used with the ccd data
            with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
                mock_identify.return_value = (['imviz'], self.ccd)

                result = jdaviz_open(self.test_file, show=False, local_path=local_path)

                mock_download.assert_called_once_with(self.test_file,
                                                      cache=True,
                                                      local_path=local_path)
                assert isinstance(result, Imviz)

                # When multiple compatible helpers are found, NotImplementedError is raised.
                mock_identify.return_value = (['imviz', 'cubeviz'], self.ccd)

                msg = 'Multiple helpers provided'
                with pytest.raises(NotImplementedError, match=msg):
                    jdaviz_open(self.test_file, show=False)


class TestLaunchConfigWithData:
    """
    Test the _launch_config_with_data() function.
    """
    @pytest.mark.parametrize(('data', 'verbosity', 'history_verbosity'),
                             [(None, None, None),
                              ('', DEFAULT_VERBOSITY, DEFAULT_HISTORY_VERBOSITY),
                              ('', 'debug', 'info')])
    def test_launch_config_basic(self, imviz_helper, data, verbosity, history_verbosity):
        """
        Test basic launching of a config without data.
        """
        kwargs = dict(data=data, verbosity=verbosity,
                      history_verbosity=history_verbosity, show=False)
        if verbosity is None:
            kwargs.pop('verbosity')
        if history_verbosity is None:
            kwargs.pop('history_verbosity')

        # mock the config class, but we can use the imviz_helper fixture here
        # (as opposed to the test below which also mocks the helper)
        # since we're not actually attempting to load anything.
        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=imviz_helper)

            result = _launch_config_with_data('imviz', **kwargs)

            mock_configs.Imviz.assert_called_once_with(
                verbosity=DEFAULT_VERBOSITY if verbosity is None else verbosity,
                history_verbosity=DEFAULT_HISTORY_VERBOSITY if history_verbosity is None else history_verbosity)  # noqa
            assert result == imviz_helper

    def test_launch_config_with_data_loads_successfully(self):
        """
        Test launching config with data that loads successfully.
        """
        mock_helper = Mock()
        mock_helper.load_data = Mock()
        mock_helper.show = Mock()

        # mock the config class to return our mock helper
        # so that we don't have to worry about the actual loading logic
        # from load_data.
        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            result = _launch_config_with_data('imviz',
                                              data=self.ccd,
                                              show=False,
                                              data_label='test')

            mock_helper.load_data.assert_called_once_with(self.ccd, data_label='test')
            mock_helper.show.assert_not_called()
            assert result == mock_helper

    def test_launch_config_with_data_io_errors(self):
        """
        Test that when loading data raises IORegistryError.
        Check with filepath fallback and without.
        """
        mock_helper = Mock()
        mock_helper.load_data = Mock(side_effect=[IORegistryError('Failed'), None])
        mock_helper.show = Mock()

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            _ = _launch_config_with_data('imviz',
                                         data=self.ccd,
                                         filepath=self.test_file)

            assert mock_helper.load_data.call_count == 2
            # Check that show is called because show=True (default)
            mock_helper.show.assert_called_once()
            mock_helper.load_data.assert_any_call(self.ccd)
            mock_helper.load_data.assert_any_call(self.test_file)

        # Now check that without filepath, the error is raised.
        mock_helper.load_data = Mock(side_effect=IORegistryError('Failed'))

        with patch('jdaviz.core.launcher.jdaviz_configs') as mock_configs:
            mock_configs.Imviz = Mock(return_value=mock_helper)

            with pytest.raises(IORegistryError, match='Failed'):
                _launch_config_with_data('imviz', data='some_data', show=False)


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
        assert launcher.file_browser_visible is False
        assert launcher.file_browser_widget is None
        for config in ALL_JDAVIZ_CONFIGS:
            assert config in launcher.config_icons

    def test_launcher_init_with_custom_init(self):
        """
        Test Launcher initialization with custom config list.
        """
        custom_configs = ['imviz', 'specviz']
        launcher = Launcher(configs=custom_configs)

        assert launcher.configs == custom_configs
        assert launcher.compatible_configs == custom_configs

        launcher = Launcher(height=600)
        assert launcher.height == '600px'

        launcher = Launcher(height='100%')
        assert launcher.height == '100%'

        # Test main_with_launcher property returns main with launcher as child.
        result = launcher.main_with_launcher
        assert result == launcher.main
        assert launcher.main.children == [launcher]

        mock_main = Mock()
        launcher = Launcher(main=mock_main)
        assert launcher.main == mock_main

        # vdocs is set to 'latest' for dev versions.
        with patch('jdaviz.core.launcher.__version__', '1.0.dev'):
            launcher = Launcher()
            assert launcher.vdocs == 'latest'

        with patch('jdaviz.core.launcher.__version__', '1.2.3'):
            launcher = Launcher()
            assert launcher.vdocs == 'v1.2.3'

        # Test that JDAVIZ_START_DIR environment variable is respected.
        test_dir = '/custom/start/dir'
        # Use patch.dict to temporarily set the environment variable.
        with patch.dict(os.environ, {'JDAVIZ_START_DIR': test_dir}):
            launcher = Launcher()
            launcher.vue_open_file_dialog()
            assert Path(launcher.file_browser_dir.value) == Path(os.path.abspath(test_dir))

    def test_launcher_init_with_filepath(self):
        """
        Test Launcher initialization with various filepaths.
        """
        launcher = Launcher()

        launcher.filepath = 'something that does not exist'
        assert launcher.hint == STATUS_HINTS['invalid path']
        assert launcher.compatible_configs == []
        assert launcher.loaded_data is None

        # Then reset and check that we're in an idle state
        launcher.filepath = ''
        assert launcher.hint == STATUS_HINTS['idle']
        assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
        assert launcher.loaded_data is None

        with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
            mock_identify.return_value = (['imviz'], self.ccd)

            launcher = Launcher(filepath=self.test_file)

            assert launcher.filepath == self.test_file
            assert launcher.hint == STATUS_HINTS['id ok']
            assert launcher.compatible_configs == ['imviz']
            assert launcher.loaded_data == self.ccd

    def test_filepath_changed_identify(self):
        """
        Test that identification failure shows all configs and uses
        filepath as data. Also test when identify_helper returns empty config list
        with None data - should leave loaded_data as None.
        """
        with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
            mock_identify.side_effect = Exception('Identification failed')

            launcher = Launcher()
            launcher.filepath = self.test_file

            assert launcher.hint == STATUS_HINTS['id failed']
            assert launcher.compatible_configs == ALL_JDAVIZ_CONFIGS
            assert launcher.loaded_data == self.test_file

        with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
            mock_identify.return_value = ([], None)

            launcher = Launcher()
            launcher.filepath = self.test_file

            # When configs is empty but data is None, loaded_data stays None
            assert launcher.loaded_data is None
            assert launcher.compatible_configs == []

    def test_vue_choose_file(self, tmp_path):
        """
        Test vue_choose_file with various scenarios.
        """
        launcher = Launcher()
        launcher.vue_open_file_dialog()
        assert launcher.file_browser_widget is not None

        # No file
        launcher.selected_file.value = ''
        launcher.vue_choose_file()

        assert launcher.filepath == ''

        # Choose with directory (should not update filepath)
        launcher.selected_file.value = 'somedir'
        launcher.file_browser_dir.value = str(tmp_path)
        launcher.file_browser_visible = True

        launcher.vue_choose_file()

        # Should close dialog even if it's a directory
        assert launcher.file_browser_visible is False

        with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
            mock_identify.return_value = (['imviz'], self.ccd)

            test_file_path = Path(self.test_file)
            launcher.file_browser_dir.value = test_file_path.parent
            launcher.selected_file.value = test_file_path.name

            launcher.vue_choose_file()

            assert launcher.file_browser_visible is False
            assert launcher.filepath == self.test_file

    @pytest.mark.parametrize('height', ['600', '100%', '100vh'])
    def test_vue_launch_config(self, deconfigged_helper, height):
        """
        Test vue_launch_config method.
        """
        mock_helper = Mock()
        dcf_app = deconfigged_helper.app
        mock_helper.app = dcf_app
        default_height = '800px'
        dcf_app.state.settings = {'context': {'notebook': {'max_height': default_height}}}
        dcf_app.layout = widgets.Layout(height=height, width="100%")

        with patch('jdaviz.core.launcher.identify_helper') as mock_identify:
            mock_identify.return_value = (['imviz'], self.ccd)

            with patch('jdaviz.core.launcher._launch_config_with_data') as mock_launch:
                mock_launch.return_value = mock_helper

                launcher = Launcher(height=height)
                launcher.filepath = self.test_file

                event = {'config': 'imviz'}
                launcher.vue_launch_config(event)

                mock_launch.assert_called_once_with('imviz',
                                                    self.ccd,
                                                    filepath=self.test_file,
                                                    show=False)

                assert launcher.main.color == 'transparent'
                assert launcher.main.children == [dcf_app]

                if height not in ['100%', '100vh']:
                    assert dcf_app.layout.height == default_height
                    assert launcher.main.height == default_height


class TestShowLauncher:
    """
    Test the show_launcher() function.
    """
    def test_show_launcher_default(self):
        """
        Test show_launcher with default parameters.
        """
        # Patch the Launcher class to avoid full initialization
        # and unintended side effects.
        with patch('jdaviz.core.launcher.Launcher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.main_with_launcher = Mock()
            mock_launcher_class.return_value = mock_launcher

            # Patch show_widget to avoid display calls.
            with patch('jdaviz.core.launcher.show_widget') as mock_show:
                show_launcher()

                mock_launcher_class.assert_called_once_with(None, ALL_JDAVIZ_CONFIGS, '', '450px')
                mock_show.assert_called_once_with(
                    mock_launcher.main_with_launcher,
                    loc='inline',
                    title=None)

    @pytest.mark.parametrize(('height', 'str_height'),
                             [(800, '800px'),
                              ('100%', '100%'),
                              ('100vh', '100vh')])
    def test_show_launcher_with_custom_params(self, height, str_height):
        """
        Test show_launcher with custom parameters.
        """
        custom_configs = ['imviz', 'specviz']
        custom_filepath = '/path/to/file.fits'

        with patch('jdaviz.core.launcher.Launcher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.main_with_launcher = Mock()
            mock_launcher_class.return_value = mock_launcher

            with patch('jdaviz.core.launcher.show_widget') as _:
                show_launcher(configs=custom_configs, filepath=custom_filepath, height=height)

                mock_launcher_class.assert_called_once_with(
                    None,
                    custom_configs,
                    custom_filepath,
                    str_height)
