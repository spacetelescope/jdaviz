#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

# NOTE: The configuration for the package, including the name, version, and
# other information are set in the setup.cfg file.

import os
import shutil
import sys

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
    import pathlib
    from tempfile import mkdtemp

    env = os.environ
    home_dir = pathlib.Path.home().as_posix()

    if env.get('JUPYTER_NO_CONFIG'):
        return mkdtemp(suffix='jupyter-clean-cfg')

    if env.get('JUPYTER_CONFIG_DIR'):
        return env['JUPYTER_CONFIG_DIR']

    return os.path.join(home_dir, '.jupyter')


def user_dir():
    homedir = os.path.expanduser('~')
    # Next line will make things work even when /home/ is a symlink to
    # /usr/home as it is on FreeBSD, for example
    homedir = os.path.realpath(homedir)
    if sys.platform == 'darwin':
        return os.path.join(homedir, 'Library', 'Jupyter')
    elif os.name == 'nt':
        appdata = os.environ.get('APPDATA', None)
        if appdata:
            return os.path.join(appdata, 'jupyter')
        else:
            return os.path.join(jupyter_config_dir(), 'data')
    else:
        # Linux, non-OS X Unix, AIX, etc.
        import pathlib
        env = os.environ
        home = pathlib.Path.home().as_posix()
        xdg = env.get("XDG_DATA_HOME", None)
        if not xdg:
            xdg = os.path.join(home, '.local', 'share')
        return os.path.join(xdg, 'jupyter')


class DevelopCmd(develop):
    prefix_targets = [
        (os.path.join("nbconvert", "templates"), 'jdaviz-default'),
        (os.path.join("voila", "templates"), 'jdaviz-default')
    ]

    def run(self):
        target_dir = os.path.join(sys.prefix, 'share', 'jupyter')
        if '--user' in sys.prefix:  # TODO: is there a better way to find out?
            target_dir = user_dir()
        target_dir = os.path.join(target_dir)

        for prefix_target, name in self.prefix_targets:
            source = os.path.join('share', 'jupyter', prefix_target, name)
            target = os.path.join(target_dir, prefix_target, name)
            target_subdir = os.path.dirname(target)
            if not os.path.exists(target_subdir):
                os.makedirs(target_subdir)
            abs_source = os.path.abspath(source)

            try:
                rel_source = os.path.relpath(abs_source, os.path.abspath(target_subdir))
            except Exception:
                # relpath does not work if source/target on different Windows disks.
                do_symlink = False
            else:
                do_symlink = True

            try:
                os.remove(target)
            except Exception:
                try:
                    shutil.rmtree(target)  # Maybe not a symlink
                except Exception:
                    pass

            # Cannot symlink without relpath or Windows admin priv in some OS versions.
            try:
                if do_symlink:
                    print(rel_source, '->', target)
                    os.symlink(rel_source, target)
                else:
                    raise OSError('just make copies')
            except Exception:
                print(abs_source, '->', target)
                shutil.copytree(abs_source, target)

        super(DevelopCmd, self).run()


# WARNING: all files generated during setup.py will not end up in the source
# distribution
data_files = []
# Add all the templates
for (dirpath, dirnames, filenames) in os.walk('share/jupyter/'):
    if filenames:
        data_files.append((dirpath, [os.path.join(dirpath, filename)
                                     for filename in filenames]))


setup(data_files=data_files, cmdclass={'develop': DevelopCmd},
      use_scm_version={'write_to': os.path.join('jdaviz', 'version.py'),
                       'write_to_template': VERSION_TEMPLATE})
