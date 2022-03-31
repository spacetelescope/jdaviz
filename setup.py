#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

# NOTE: The configuration for the package, including the name, version, and
# other information are set in the setup.cfg file.

import os
import shutil
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.develop import develop


# First provide helpful messages if contributors try and run legacy commands
# for tests or docs.

TEST_HELP = """
Note: running tests is no longer done using 'python setup.py test'. Instead
you will need to run:

    tox -e test

If you don't already have tox installed, you can install it with:

    pip install tox

If you only want to run part of the test suite, you can also use pytest
directly with::

    pip install -e .[test]
    pytest

For more information, see:

  http://docs.astropy.org/en/latest/development/testguide.html#running-tests
"""

if 'test' in sys.argv:
    print(TEST_HELP)
    sys.exit(1)

DOCS_HELP = """
Note: building the documentation is no longer done using
'python setup.py build_docs'. Instead you will need to
build the documentation with Sphinx directly using::

    pip install -e .[docs]
    cd docs
    make html

For more information, see:

  http://docs.astropy.org/en/latest/install.html#builddocs
"""

if 'build_docs' in sys.argv or 'build_sphinx' in sys.argv:
    print(DOCS_HELP)
    sys.exit(1)

VERSION_TEMPLATE = """
# Note that we need to fall back to the hard-coded version if either
# setuptools_scm can't be imported or setuptools_scm can't determine the
# version, so we catch the generic 'Exception'.
try:
    from setuptools_scm import get_version
    version = get_version(root='..', relative_to=__file__)
except Exception:
    version = '{version}'
""".lstrip()


# These are based on jupyter_core.paths
def jupyter_config_dir():
    """Get the Jupyter config directory for this platform and user.
    Returns JUPYTER_CONFIG_DIR if defined, else ~/.jupyter
    """
    from tempfile import mkdtemp

    env = os.environ
    home_dir = Path.home()

    if env.get('JUPYTER_NO_CONFIG'):
        return Path(mkdtemp(suffix='jupyter-clean-cfg'))

    if env.get('JUPYTER_CONFIG_DIR'):
        return Path(env['JUPYTER_CONFIG_DIR'])

    return home_dir / '.jupyter'


def user_dir():
    if sys.platform == 'darwin':
        # realpath will make things work even when /home/ is a symlink to
        # /usr/home as it is on FreeBSD, for example
        return Path(os.path.realpath(os.path.expanduser('~'))) / 'Library' / 'Jupyter'
    elif sys.platform.startswith('win'):
        appdata = os.environ.get('APPDATA', None)
        if appdata:
            return Path(appdata, 'jupyter')
        else:
            return jupyter_config_dir() / 'data'
    # Linux, non-OS X Unix, AIX, etc.
    elif "XDG_DATA_HOME" in os.environ:
        return Path(os.environ["XDG_DATA_HOME"], 'jupyter')
    else:
        return Path.home() / '.local' / 'share' / 'jupyter'


class DevelopCmd(develop):
    prefix_targets = [
        (Path("nbconvert", "templates"), 'jdaviz-default'),
        (Path("voila", "templates"), 'jdaviz-default')
    ]

    def run(self):
        if '--user' in sys.prefix:  # TODO: is there a better way to find out?
            target_dir = user_dir()
        else:
            target_dir = Path(sys.prefix, 'share', 'jupyter')

        is_win = sys.platform.startswith('win')

        for prefix_target, name in self.prefix_targets:
            source = Path('share', 'jupyter') / prefix_target / name
            target = target_dir / prefix_target / name
            target_subdir = target.parent
            target_subdir.mkdir(parents=True, exist_ok=True)
            rel_source = source.resolve(strict=True)
            print(rel_source, '->', target)

            if not is_win:
                rel_source = rel_source.relative_to(target_subdir.resolve(strict=True))
                target.unlink()
                target.symlink_to(rel_source)
            else:  # Cannot symlink without relpath or Windows admin priv in some OS versions
                # Beware: https://docs.python.org/3/library/shutil.html#shutil.rmtree.avoids_symlink_attacks  # noqa
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(rel_source, target)

        super(DevelopCmd, self).run()


# WARNING: all files generated during setup.py will not end up in the source
# distribution
data_files = []
# Add all the templates
for (dirpath, dirnames, filenames) in os.walk('share/jupyter/'):
    if filenames:
        data_files.append((dirpath, [Path(dirpath, filename)
                                     for filename in filenames]))


setup(data_files=data_files, cmdclass={'develop': DevelopCmd},
      use_scm_version={'write_to': Path('jdaviz', 'version.py'),
                       'write_to_template': VERSION_TEMPLATE})
