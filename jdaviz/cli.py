# Command-line interface for jdaviz

import inspect
import os
import pathlib

from jdaviz import __version__
from jdaviz.app import _verbosity_levels, ALL_JDAVIZ_CONFIGS
from jdaviz import configs

__all__ = ['main']

CONFIGS_DIR = str(pathlib.Path(inspect.getfile(configs)).parent)
JDAVIZ_DIR = pathlib.Path(__file__).parent.resolve()
DEFAULT_VERBOSITY = 'warning'
DEFAULT_HISTORY_VERBOSITY = 'info'


def main(filepaths=None, layout='default', instrument=None, browser='default',
         theme='auto', verbosity=DEFAULT_VERBOSITY, history_verbosity=DEFAULT_HISTORY_VERBOSITY,
         host='localhost', port=0, hotreload=False):
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
    theme : {'auto', 'light', 'dark'}
        Theme to use for application.
    verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the popup messages in the application.
    history_verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the history logger in the application.
    host : str, optional
        Host to bind the server to, default is 'localhost'.
    port : int, optional
        Port to bind the server to, default is 0 (finds an empty port).
    hotreload : bool
        Whether to enable hot-reloading of the UI (for development)
    """
    if filepaths:
        # Convert paths to posix string; windows paths are not JSON compliant
        file_list = [pathlib.Path(f).absolute().as_posix() for f in filepaths]
        if layout == "imviz":
            # Imviz multiloading should be done all at once for batch processing.
            # Imviz convention is a single string of consecutive, comma-separated file paths
            file_list = [','.join(file_list)]
    else:
        file_list = []

    if layout == '' and len(file_list) > 1:
        raise ValueError("'layout' argument is required when specifying multiple files")

    # Keep track of start directory in environment variable so that it can be
    # easily accessed e.g. in the file load dialog.
    os.environ['JDAVIZ_START_DIR'] = os.path.abspath('.')

    from jdaviz import solara
    solara.config = layout.capitalize()
    solara.data_list = file_list
    if layout == 'mosviz':
        solara.load_data_kwargs = {'instrument': instrument}
    solara.theme = theme
    solara.jdaviz_verbosity = verbosity
    solara.jdaviz_history_verbosity = history_verbosity
    run_solara(host=host, port=port, theme=theme, browser=browser, production=not hotreload)


def run_solara(host, port, theme, browser, production: bool = True):
    os.environ["SOLARA_APP"] = "jdaviz.solara"
    import solara.server.starlette
    import solara.server.settings
    solara.server.settings.theme.variant = theme
    solara.server.settings.theme.loader = "plain"
    solara.server.settings.main.mode = "production" if production else "development"

    server = solara.server.starlette.ServerStarlette(host="localhost", port=port)
    print(f"Starting server on {server.base_url}")
    server.serve_threaded()
    server.wait_until_serving()
    if browser == "qt":
        from . import qt
        qt.run_qt(server.base_url)
    else:
        import webbrowser
        controller = webbrowser.get(None if browser == 'default' else browser)
        controller.open(server.base_url)
        server.join()


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
                        help='Browser to use for application (use qt for embedded Qt browser).')
    parser.add_argument('--theme', choices=['light', 'dark'], default='light',
                        help='Theme to use for application.')
    parser.add_argument('--verbosity', choices=_verbosity_levels, default='info',
                        help='Verbosity of the application for popup snackbars.')
    parser.add_argument('--history-verbosity', choices=_verbosity_levels, default='info',
                        help='Verbosity of the logger history.')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Host to bind the server to, defaults to localhost.')
    parser.add_argument('--port', type=int, default=0,
                        help='Port to bind the server to, defaults to 0 (finds an empty port).')
    # Also enables --no-hotreload
    parser.add_argument('--hotreload', action=argparse.BooleanOptionalAction, default=False,
                        help='Whether to enable hot-reloading of the UI (for development).')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()

    if config is None:
        layout = args.layout
    else:
        layout = config

    main(filepaths=args.filepaths, layout=layout, instrument=args.instrument, browser=args.browser,
         theme=args.theme, verbosity=args.verbosity, history_verbosity=args.history_verbosity,
         host=args.host, port=args.port, hotreload=args.hotreload)


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
