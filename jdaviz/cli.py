# Command-line interface for jdaviz

import os
import sys
import tempfile

import click
from voila.app import Voila

NOTEBOOK_TEMPLATE = r"""
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "scrolled": false
   },
   "outputs": [],
   "source": [
    "from jdaviz.app import IPyApplication\n",
    "app = IPyApplication(configuration='CONFIG_NAME')\n",
    "app._application_handler.load_data('DATA_FILENAME')\n",
    "app"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.4"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""


@click.command()
@click.argument('filename')
@click.option('--layout', default='default')
def main(filename, layout):

    start_dir = os.path.abspath('.')

    nbdir = tempfile.mkdtemp()
    with open(os.path.join(nbdir, 'notebook.ipynb'), 'w') as nbf:
        nbf.write(NOTEBOOK_TEMPLATE.replace('CONFIG_NAME', layout).replace('DATA_FILENAME', filename).strip())

    os.chdir(nbdir)
    try:
        Voila.notebook_path = 'notebook.ipynb'
        sys.exit(Voila().launch_instance())
    finally:
        os.chdir(start_dir)
