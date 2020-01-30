#!/usr/bin/env python

# Licensed under a 3-clause BSD style license - see LICENSE.rst

import sys
import os
import builtins
import contextlib

# Ensure that astropy-helpers is available
import ah_bootstrap  # noqa

from setuptools import setup
from setuptools.config import read_configuration
from setuptools.command.develop import develop

from astropy_helpers.setup_helpers import register_commands, get_package_info
from astropy_helpers.version_helpers import generate_version_py

# Store the package name in a built-in variable so it's easy
# to get from other parts of the setup infrastructure
builtins._ASTROPY_PACKAGE_NAME_ = read_configuration('setup.cfg')[
    'metadata']['name']

# Create a dictionary with setup command overrides. Note that this gets
# information about the package (name and version) from the setup.cfg file.
cmdclass = register_commands()

# Freeze build information in version.py. Note that this gets information
# about the package (name and version) from the setup.cfg file.
version = generate_version_py()

# Get configuration information from all of the various subpackages.
# See the docstring for setup_helpers.update_package_files for more
# details.
package_info = get_package_info()

# Include extra data files not picked up in the astropy helpers functions.
# WARNING: all files generates during setup.py will not end up in the
# source distribution
data_files = []

for (dirpath, dirnames, filenames) in os.walk('share/jupyter/voila/templates/'):
    if filenames:
        data_files.append((dirpath, [os.path.join(dirpath, filename)
                                     for filename in filenames]))

# These are based on jupyter_core.paths


def jupyter_config_dir():
    """Get the Jupyter config directory for this platform and user.

    Returns JUPYTER_CONFIG_DIR if defined, else ~/.jupyter
    """

    env = os.environ
    home_dir = get_home_dir()

    if env.get('JUPYTER_NO_CONFIG'):
        return _mkdtemp_once('jupyter-clean-cfg')

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
        xdg = env.get("XDG_DATA_HOME", None)
        if not xdg:
            xdg = os.path.join(home, '.local', 'share')
        return os.path.join(xdg, 'jupyter')


class DevelopCmd(develop):
    prefix_targets = [
        ("voila/templates", 'jdaviz-default'),
        ("voila/templates", 'custom')
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
            rel_source = (os.path.relpath(os.path.abspath(source),
                                          os.path.abspath(target_subdir)))
            try:
                os.remove(target)
            except:
                pass

            os.symlink(rel_source, target)

        super(DevelopCmd, self).run()


cmdclass.update({'develop': DevelopCmd})

setup(version=version, cmdclass=cmdclass, include_package_data=True,
      data_files=data_files, **package_info)
