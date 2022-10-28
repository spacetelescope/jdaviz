#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

# NOTE: The configuration for the package, including the name, version, and
# other information are set in the setup.cfg file.

import os
import sys
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command import install, develop

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


# WARNING: all files generated during setup.py will not end up in the source
# distribution
data_files = []
# Add the jdaviz voila template files for installations via either
# `python setup.py install` or `pip install .` (but not `pip install -e .`)
for (dirpath, dirnames, filenames) in os.walk('share/jupyter/'):
    if filenames:
        data_files.append((dirpath, [os.path.join(dirpath, filename)
                                     for filename in filenames]))


# These are based on jupyter_core.paths
def jupyter_config_dir():
    """Get the Jupyter config directory for this platform and user.
    Returns JUPYTER_CONFIG_DIR if defined, else ~/.jupyter
    """
    from tempfile import mkdtemp

    env = os.environ
    home_dir = Path.home().as_posix()

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
        env = os.environ
        home = Path.home().as_posix()
        xdg = env.get("XDG_DATA_HOME", None)
        if not xdg:
            xdg = os.path.join(home, '.local', 'share')
        return os.path.join(xdg, 'jupyter')


def get_existing_template_dirs(app_names, template_name):
    # to do this import, voila must be required in pyproject.toml
    from voila.paths import collect_template_paths

    return [
        d for d in collect_template_paths(app_names, template_name)
        if os.path.exists(d) and template_name in d
    ]


def install_jdaviz_voila_template(
    template_name='jdaviz-default', reference_template_name='lab', overwrite=False
):
    """
    Make the ``jdaviz-default`` template available for use with voila.

    Generate copies of/symbolic links pointing towards the jdaviz template files
    in the directories where voila expects them.
    """
    # search for existing "jdaviz-default" and "lab" (default) template paths
    # already installed on this machine:
    app_names = ['nbconvert', 'voila']
    jdaviz_template_dirs = get_existing_template_dirs(app_names, template_name)
    reference_template_dirs = get_existing_template_dirs(app_names, reference_template_name)

    # if there are existing jdaviz template dirs but overwrite=False, raise error:
    if not overwrite and len(jdaviz_template_dirs):
        raise FileExistsError(
            f"Existing files found at {jdaviz_template_dirs} which "
            f"would be overwritten, but overwrite=False."
        )

    prefix_targets = [
        os.path.join("nbconvert", "templates"),
        os.path.join("voila", "templates")
    ]

    repo_top_level_dir = Path(__file__)

    if len(reference_template_dirs):
        target_dir = Path(reference_template_dirs[0]).absolute().parents[2]
    else:
        raise FileNotFoundError(f"No {reference_template_name} template found for voila.")

    for prefix_target in prefix_targets:
        source = os.path.join(repo_top_level_dir, 'share', 'jupyter', prefix_target, template_name)
        parent_dir_of_target = os.path.join(target_dir, prefix_target)
        target = os.path.join(parent_dir_of_target, template_name)
        abs_source = os.path.abspath(source)
        try:
            rel_source = os.path.relpath(abs_source, parent_dir_of_target)
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
                print('making symlink:', rel_source, '->', target)
                os.symlink(rel_source, target)
            else:
                raise OSError('just make copies')
        except Exception:
            print('making copy:', abs_source, '->', target)
            shutil.copytree(abs_source, target)


class CmdMixin:
    """
    If you pip install from source with `pip install .` or with
    `python setup.py install` (deprecated) or `python setup.py develop`,
    this will try to symlink or copy the voila template files to the
    correct locations. Warning: if you run editable install with
    `pip install -e .`, this will not be called.
    """
    def run(self):
        install_jdaviz_voila_template(overwrite=True)
        super().run()


class InstallCmd(CmdMixin, install.install):
    pass


class DevelopCmd(CmdMixin, develop.develop):
    pass


setup(data_files=data_files, cmdclass={'install': InstallCmd, 'develop': DevelopCmd},
      use_scm_version={'write_to': os.path.join('jdaviz', 'version.py'),
                       'write_to_template': VERSION_TEMPLATE})
