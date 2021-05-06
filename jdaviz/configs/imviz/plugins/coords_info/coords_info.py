from traitlets import Unicode

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template = load_template("coords_info.vue", __file__).tag(sync=True)
    pixel = Unicode("").tag(sync=True)
    world = Unicode("").tag(sync=True)
    value = Unicode("").tag(sync=True)
