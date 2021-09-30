from traitlets import List, Unicode, Bool

from jdaviz.configs.imviz.helper import link_image_data
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['LinksControl']


@tray_registry('imviz-links-control', label="Imviz Links Control")
class LinksControl(TemplateMixin):
    template = load_template("links_control.vue", __file__).tag(sync=True)

    link_types = List(['Pixels', 'WCS']).tag(sync=True)

    # default states. NOTE: same case as options above, any necessary casting
    # to internal API formats should be in vue_do_link)
    link_type = Unicode('Pixels').tag(sync=True)
    wcs_use_fallback = Bool(True).tag(sync=True)
    wcs_use_affine = Bool(True).tag(sync=True)

    def vue_do_link(self, *args, **kwargs):
        """Run :func:`jdaviz.configs.imviz.helper.link_image_data`
        with the selected parameters.
        """
        link_image_data(
            self.app,
            link_type=self.link_type.lower(),
            wcs_fallback_scheme='pixels' if self.wcs_use_fallback else None,
            wcs_use_affine=self.wcs_use_affine,
            error_on_fail=False)
