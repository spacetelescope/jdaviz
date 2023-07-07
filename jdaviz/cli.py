# Command-line interface for jdaviz

import inspect
import os
import pathlib
import sys
import tempfile

from voila.app import Voila
from voila.configuration import VoilaConfiguration

from jdaviz import __version__
from jdaviz.app import _verbosity_levels
from jdaviz import configs

__all__ = ['main']

CONFIGS_DIR = str(pathlib.Path(inspect.getfile(configs)).parent)
JDAVIZ_DIR = pathlib.Path(__file__).parent.resolve()
DEFAULT_VERBOSITY = 'warning'
DEFAULT_HISTORY_VERBOSITY = 'info'
ALL_JDAVIZ_CONFIGS = ['cubeviz', 'specviz', 'specviz2d', 'mosviz', 'imviz']


def main(filepaths=None, layout='default', instrument=None, browser='default',
         theme='light', verbosity=DEFAULT_VERBOSITY, history_verbosity=DEFAULT_HISTORY_VERBOSITY,
         hotreload=False):
    """
    Start a Jdaviz application instance with data loaded from FILENAME.

    Parameters
    ----------
    filepaths : list of str, optional
        List of paths to the file(s) to be loaded into the Jdaviz application.
    layout : str, optional
        Optional specification for which configuration to use on startup.
    instrument : str, optional
        Specifies which instrument parser to use for Mosviz, if applicable.
    browser : str, optional
        Path to browser executable.
    theme : {'light', 'dark'}
        Theme to use for Voila app or Jupyter Lab.
    verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the popup messages in the application.
    history_verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the history logger in the application.
    hotreload : bool
        Whether to enable hot-reloading of the UI (for development)
    """
    import logging  # Local import to avoid possibly messing with JWST pipeline logger.

    # Tornado Webserver py3.8 compatibility hotfix for windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    if filepaths:
        # Convert paths to posix string; windows paths are not JSON compliant
        file_list = [pathlib.Path(f).absolute().as_posix() for f in filepaths]
        if layout == "imviz":
            # Imviz multiloading should be done all at once for batch processing.
            # Imviz convention is a single string of consecutive, comma-separated file paths
            file_list = [','.join(file_list)]
    else:
        file_list = []

    if len(file_list) == 0 and layout == '':
        notebook = "jdaviz_cli_launcher.ipynb"
    else:
        notebook = "jdaviz_cli.ipynb"

    with open(JDAVIZ_DIR / notebook) as f:
        notebook_template = f.read()

    start_dir = os.path.abspath('.')

    # Keep track of start directory in environment variable so that it can be
    # easily accessed e.g. in the file load dialog.
    os.environ['JDAVIZ_START_DIR'] = start_dir

    nbdir = tempfile.mkdtemp()

    if hotreload:
        notebook_template = notebook_template.replace("# PREFIX", "from jdaviz import enable_hot_reloading; enable_hot_reloading()")  # noqa: E501

    with open(os.path.join(nbdir, 'notebook.ipynb'), 'w') as nbf:
        nbf.write(
            notebook_template
            .replace('CONFIG', layout.capitalize())
            .replace('DATA_LIST', str(file_list))
            .replace('JDAVIZ_VERBOSITY', verbosity)
            .replace('JDAVIZ_HISTORY_VERBOSITY', history_verbosity)
            # Mosviz specific changes
            .replace('load_data(data', 'load_data(directory=data' if layout == 'mosviz' else 'load_data(data')  # noqa: E501
            .replace(') #ADDITIONAL_LOAD_DATA_ARGS', f', instrument=\'{instrument}\')' if layout == 'mosviz' else ')')  # noqa: E501
            .strip()
        )

    os.chdir(nbdir)

    try:
        logging.getLogger('tornado.access').disabled = True
        Voila.notebook_path = 'notebook.ipynb'
        VoilaConfiguration.template = 'jdaviz-default'
        VoilaConfiguration.enable_nbextensions = True
        VoilaConfiguration.file_whitelist = ['.*']
        VoilaConfiguration.theme = theme
        if browser != 'default':
            Voila.browser = browser
        sys.exit(Voila().launch_instance(argv=[]))
    finally:
        os.chdir(start_dir)


def _main(config=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Start a Jdaviz application instance with data '
                                     'loaded from FILENAME.')
    filepaths_nargs = '*'
    if config is None:
        parser.add_argument('--layout', default='', choices=ALL_JDAVIZ_CONFIGS,
                            help='Configuration to use.')
    if (config == "mosviz") or ("mosviz" in sys.argv):
        filepaths_nargs = 1
    parser.add_argument('filepaths', type=str, nargs=filepaths_nargs, default=None,
                        help='The paths to the files to be loaded into the Jdaviz application.')
    parser.add_argument('--instrument', type=str, default='nirspec',
                        help='Manually specifies which instrument parser to use, for Mosviz')
    parser.add_argument('--browser', type=str, default='default',
                        help='Browser to use for application.')
    parser.add_argument('--theme', choices=['light', 'dark'], default='light',
                        help='Theme to use for application.')
    parser.add_argument('--verbosity', choices=_verbosity_levels, default='info',
                        help='Verbosity of the application for popup snackbars.')
    parser.add_argument('--history-verbosity', choices=_verbosity_levels, default='info',
                        help='Verbosity of the logger history.')
    if sys.version_info >= (3, 9):
        # Also enables --no-hotreload
        parser.add_argument('--hotreload', action=argparse.BooleanOptionalAction, default=False,
                            help='Whether to enable hot-reloading of the UI (for development).')
    else:
        parser.add_argument('--hotreload', action='store_true', default=False,
                            help='Enable hot-reloading of the UI (for development).')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()

    if config is None:
        layout = args.layout
    else:
        layout = config

    main(filepaths=args.filepaths, layout=layout, instrument=args.instrument, browser=args.browser,
         theme=args.theme, verbosity=args.verbosity, history_verbosity=args.history_verbosity,
         hotreload=args.hotreload)


def _specviz():
    _main(config='specviz')


def _specviz2d():
    _main(config='specviz2d')


def _imviz():
    _main(config='imviz')


def _cubeviz():
    _main(config='cubeviz')


def _mosviz():
    _main(config='mosviz')


if __name__ == "__main__":
    _main()
