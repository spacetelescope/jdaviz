# Command-line interface for jdaviz

import os
import pathlib
import sys
import tempfile

import click
from voila.app import Voila
from voila.configuration import VoilaConfiguration

from jdaviz import __version__

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'configs')


@click.version_option(__version__)
@click.command()
@click.argument('filename', nargs=1)
@click.option('--layout',
              default='default',
              nargs=1,
              show_default=True,
              type=click.Choice(['default', 'cubeviz', 'specviz', 'mosviz', 'imviz'],
                                case_sensitive=False),
              help="Configuration to use on application startup")
@click.option('--browser',
              default='default',
              nargs=1,
              show_default=True,
              type=str,
              help="Browser to use for application")
@click.option('--theme',
              default='light',
              nargs=1,
              show_default=True,
              type=click.Choice(['light', 'dark']),
              help="Theme to use for application")
@click.option('--verbosity',
              default='info',
              nargs=1,
              show_default=True,
              type=click.Choice(['debug', 'info', 'warning', 'error']),
              help="Verbosity of the application")
@click.option('--hotreload/--no-hotreload',
              default=False,
              help="Whether to enable hot-reloading of the UI (for development)")
def main(filename, layout='default', browser='default', theme='light', verbosity='info',
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
        Verbosity of the application.
    hotreload: bool
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
        nbf.write(notebook_template.replace('DATA_FILENAME', filepath).replace('JDAVIZ_VERBOSITY', verbosity).strip())  # noqa: E501

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


if __name__ == '__main__':
    main()
