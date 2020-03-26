# Command-line interface for jdaviz

import os
import sys
import tempfile

import click
from voila.app import Voila
from voila.configuration import VoilaConfiguration

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'configs')


@click.command()
@click.argument('filename')
@click.option('--layout', default='default')
def main(filename, layout):

    filename = os.path.abspath(filename)

    with open(os.path.join(CONFIGS_DIR, layout, layout + '.ipynb')) as f:
        notebook_template = f.read()

    start_dir = os.path.abspath('.')

    nbdir = tempfile.mkdtemp()
    with open(os.path.join(nbdir, 'notebook.ipynb'), 'w') as nbf:
        nbf.write(notebook_template.replace('CONFIG_NAME', layout).replace('DATA_FILENAME', filename).strip())

    os.chdir(nbdir)
    try:
        Voila.notebook_path = 'notebook.ipynb'
        VoilaConfiguration.template = 'jdaviz-default'
        VoilaConfiguration.enable_nbextensions = True
        sys.exit(Voila().launch_instance())
    finally:
        os.chdir(start_dir)
