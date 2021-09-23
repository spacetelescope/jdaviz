from traitlets import Unicode

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template_file = __file__, "coords_info.vue"
    pixel = Unicode("").tag(sync=True)
    world = Unicode("").tag(sync=True)
    value = Unicode("").tag(sync=True)
