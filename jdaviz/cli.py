# Command-line interface for jdaviz

import os
import pathlib
import sys
import tempfile

from voila.app import Voila
from voila.configuration import VoilaConfiguration

from jdaviz import __version__
from jdaviz.app import _verbosity_levels

__all__ = ['main']

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'configs')


def main(filename, layout='default', browser='default', theme='light',
         verbosity='warning', history_verbosity='info',
         hotreload=False):
    """
    Start a Jdaviz application instance with data loaded from FILENAME.

    Parameters
    ----------
    filename : str
        The path to the file to be loaded into the Jdaviz application.
    layout : str, optional
        Optional specification for which configuration to use on startup.
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

    # Support comma-separate file list
    filepath = ','.join([str(pathlib.Path(f).absolute()).replace('\\', '/')
                         for f in filename.split(',')])

    with open(os.path.join(CONFIGS_DIR, layout, layout + '.ipynb')) as f:
        notebook_template = f.read()

    start_dir = os.path.abspath('.')

    # Keep track of start directory in environment variable so that it can be
    # easily accessed e.g. in the file load dialog.
    os.environ['JDAVIZ_START_DIR'] = start_dir

    nbdir = tempfile.mkdtemp()

    if hotreload:
        notebook_template = notebook_template.replace("# PREFIX", "from jdaviz import enable_hot_reloading; enable_hot_reloading()")  # noqa: E501

    with open(os.path.join(nbdir, 'notebook.ipynb'), 'w') as nbf:
        nbf.write(notebook_template.replace('DATA_FILENAME', filepath).replace('JDAVIZ_VERBOSITY', verbosity).replace('JDAVIZ_HISTORY_VERBOSITY', history_verbosity).strip())  # noqa: E501

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


def _main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Start a Jdaviz application instance with data '
                                     'loaded from FILENAME.')
    parser.add_argument('layout', choices=['cubeviz', 'specviz', 'mosviz', 'imviz'],
                        help='Configuration to use.')
    parser.add_argument('filename', type=str,
                        help='The path to the file to be loaded into the Jdaviz application.')
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

    main(args.filename, layout=args.layout, browser=args.browser, theme=args.theme,
         verbosity=args.verbosity, history_verbosity=args.history_verbosity,
         hotreload=args.hotreload)
