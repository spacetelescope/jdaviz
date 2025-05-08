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
           'get_data']
_incl = ['App', 'enable_hot_reloading', '__version__']
_temporary_incl = ['open', 'Cubeviz', 'Imviz', 'Mosviz', 'Rampviz', 'Specviz', 'Specviz2d']
__all__ = _expose + _incl + _temporary_incl


global _ca

_ca = App(api_hints_obj='jd')


def __dir__():
    return sorted(__all__)


def __getattr__(name):
    if name in _expose:
        return getattr(_ca, name)
    if name in globals():
        return globals()[name]
    raise AttributeError()
