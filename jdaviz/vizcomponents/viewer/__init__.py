from glue_jupyter import set_layout_factory

from .viewernd import ViewerND  # noqa
from .viewer1d import Viewer1D  # noqa
from .layout_factory import jdaviz_layout_factory

set_layout_factory(jdaviz_layout_factory)
