# Command-line interface for jdaviz

import pathlib
import os
import sys
import tempfile

import click
from voila.app import Voila
from voila.configuration import VoilaConfiguration

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'configs')


@click.command()
@click.argument('filename', nargs=1, type=click.Path(exists=True))
@click.option('--layout',
              default='default',
              nargs=1,
              show_default=True,
              type=click.Choice(['default', 'cubeviz', 'specviz', 'mosviz',
                                 'imviz'], case_sensitive=False),
              help="Configuration to use on application startup")
def main(filename, layout='default'):
    """
    Start a JDAViz application instance with data loaded from FILENAME.\f

    Parameters
    ----------
    filename : str
        The path to the file to be loaded into the JDAViz application.
    layout : str, optional
        Optional specification for which configuration to use on startup.
    """
    # Tornado Webserver py3.8 compatibility hotfix for windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    filepath = pathlib.Path(filename).absolute()

    with open(os.path.join(CONFIGS_DIR, layout, layout + '.ipynb')) as f:
        notebook_template = f.read()

    start_dir = os.path.abspath('.')

    nbdir = tempfile.mkdtemp()

    with open(os.path.join(nbdir, 'notebook.ipynb'), 'w') as nbf:
        nbf.write(notebook_template.replace('DATA_FILENAME', str(filepath).replace('\\', '/')).strip())

    os.chdir(nbdir)

    try:
        Voila.notebook_path = 'notebook.ipynb'
        VoilaConfiguration.template = 'jdaviz-default'
        VoilaConfiguration.enable_nbextensions = True
        sys.exit(Voila().launch_instance(argv=[]))
    finally:
        os.chdir(start_dir)

if __name__ == '__main__':
    main()
