# Licensed under a 3-clause BSD style license - see LICENSE.rst

# Packages may add whatever they like to this file, but
# should keep this content at the top.
# ----------------------------------------------------------------------------
from ._astropy_init import *   # noqa
# ----------------------------------------------------------------------------

from glue_jupyter.bqplot.profile import layer_artist
layer_artist.USE_GL = False

# top-level API as exposed to users
from jdaviz.app import *  # noqa
from jdaviz.configs.specviz import Specviz, SpecViz  # noqa
from jdaviz.configs.specviz2d import Specviz2d  # noqa
from jdaviz.configs.mosviz import Mosviz, MosViz  # noqa
from jdaviz.configs.cubeviz import Cubeviz, CubeViz  # noqa
from jdaviz.configs.imviz import Imviz  # noqa
from jdaviz.utils import enable_hot_reloading  # noqa

import bqplot
from jdaviz.core.marks import BaseUnitLine
bqplot.Lines = BaseUnitLine

del layer_artist, bqplot, BaseUnitLine
