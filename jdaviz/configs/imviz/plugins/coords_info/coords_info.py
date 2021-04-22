from traitlets import Unicode

from jdaviz.core.registries import info_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['CoordsInfo']


@info_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template = load_template("coords_info.vue", __file__).tag(sync=True)
    text = Unicode("").tag(sync=True)
