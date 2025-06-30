# Licensed under a 3-clause BSD style license - see LICENSE.rst

try:
    from .version import version as __version__
except ImportError:
    __version__ = ''


# Top-level API as exposed to users.
from jdaviz.configs.cubeviz import Cubeviz  # noqa: F401
from jdaviz.configs.imviz import Imviz  # noqa: F401
from jdaviz.configs.mosviz import Mosviz  # noqa: F401
from jdaviz.configs.rampviz import Rampviz  # noqa: F401
from jdaviz.configs.specviz import Specviz  # noqa: F401
from jdaviz.configs.specviz2d import Specviz2d  # noqa: F401
from jdaviz.configs.deconfigged import App  # noqa: F401

from jdaviz.utils import enable_hot_reloading  # noqa: F401
from jdaviz.core.launcher import open  # noqa: F401


_expose = ['show', 'load', 'batch_load',
           'toggle_api_hints',
           'plugins',
           'loaders',
           'viewers',
           'new_viewers',
           'get_data']
_incl = ['enable_hot_reloading', '__version__', 'gca', 'get_all_apps', 'app']
_temporary_incl = ['open', 'Cubeviz', 'Imviz', 'Mosviz', 'Rampviz', 'Specviz', 'Specviz2d']
__all__ = _expose + _incl + _temporary_incl


global _apps
global _current_index

_apps = []


def app(replace=False, set_as_current=True):
    """
    Create a new jdaviz application instance and assign as the current instance.

    Parameters
    ----------
    replace : bool, optional
        If True, replaces the current application instance with the new one.
        Default is False, which means a new instance is added to the list of applications.
    set_as_current : bool, optional
        If True, sets the newly created application instance as the current instance.
        Default is True.

    Returns
    -------
    App
        A new instance of the App class.
    """
    global _apps
    global _current_index
    # NOTE: here we call this "App" for the user, but it is really the "deconfigged"
    # config-helper, which in turn has a .app to access the internal/private Application
    # instance.  After the other configs pass their deprecation period, we should try to
    # rename the internal Application instance and/or merge functionality in with the
    # App class to avoid confusion.
    ca = App(api_hints_obj='jd')
    if replace:
        _apps[_current_index] = ca
    else:
        _apps += [ca]
        if set_as_current:
            _current_index = len(_apps) - 1
    return ca


def get_all_apps():
    """
    Get a list of all jdaviz application instances.

    Returns
    -------
    list
        A list of all jdaviz application instances.
    """
    return _apps


def gca(index=None, set_as_current=True):
    """
    Get the current jdaviz application instance.

    Parameters
    ----------
    index : int, optional
        The index of the application instance to retrieve.
        Default is the current instance.
    set_as_current : bool, optional
        If True, sets the application instance at the specified index as the current instance.
        Default is True.

    Returns
    -------
    App
        The current jdaviz application instance.
    """
    global _current_index
    if not len(_apps):
        # on first access (either to gca() directly or anything redirected through _expose),
        # create a first instance
        app(set_as_current=True)
    if index is None:
        index = _current_index
    _app = _apps[index]
    if set_as_current:
        if index < 0:
            # make sure we have a positive index so
            # this remains fixed when adding new entries
            index = len(_apps) + index
        _current_index = index
    return _app


def __dir__():
    return sorted(__all__)


def __getattr__(name):
    if name in _expose:
        return getattr(gca(), name)
    if name in globals():
        return globals()[name]
    raise AttributeError()
