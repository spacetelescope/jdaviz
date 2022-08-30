from traitlets import List, Unicode, Bool, observe

from jdaviz.configs.imviz.helper import link_image_data
from jdaviz.core.events import LinkUpdatedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin

__all__ = ['LinksControl']


@tray_registry('imviz-links-control', label="Imviz Links Control")
class LinksControl(PluginTemplateMixin):
    template_file = __file__, "links_control.vue"

    link_types = List(['Pixels', 'WCS']).tag(sync=True)

    # default states. NOTE: same case as options above, any necessary casting
    # to internal API formats should be in vue_do_link)
    link_type = Unicode('Pixels').tag(sync=True)
    wcs_use_fallback = Bool(True).tag(sync=True)
    wcs_use_affine = Bool(True).tag(sync=True)

    linking_in_progress = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, LinkUpdatedMessage,
                           handler=self._on_link_updated)

    def _on_link_updated(self, msg):
        self.link_type = {'pixels': 'Pixels', 'wcs': 'WCS'}[msg.link_type]
        self.linking_in_progress = True
        self.wcs_use_fallback = msg.wcs_use_fallback
        self.wcs_use_affine = msg.wcs_use_affine

    @observe('link_type', 'wcs_use_fallback', 'wcs_use_affine')
    def _update_link(self, msg):
        """Run :func:`jdaviz.configs.imviz.helper.link_image_data`
        with the selected parameters.
        """
        if msg.get('name', None) == 'wcs_use_affine' and self.link_type == 'Pixels':
            # approximation doesn't apply, avoid updating when not necessary!
            return

        if self.linking_in_progress:
            return

        self.linking_in_progress = True

        if self.link_type == 'Pixels':
            # reset wcs_use_affine to be True
            self.wcs_use_affine = True

        link_image_data(
            self.app,
            link_type=self.link_type.lower(),
            wcs_fallback_scheme='pixels' if self.wcs_use_fallback else None,
            wcs_use_affine=self.wcs_use_affine,
            error_on_fail=False,
            update_plugin=False)

        self.linking_in_progress = False
