from traitlets import List

from jdaviz.configs.imviz.helper import link_image_data
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['LinksControl']


@tray_registry('imviz-links-control', label="Imviz Links Control")
class LinksControl(TemplateMixin):
    template = load_template("links_control.vue", __file__).tag(sync=True)

    # TODO: Use radio button groups?
    link_types = List(['Pixels', 'WCS']).tag(sync=True)
    wcs_fallback_schemes = List(['None', 'Pixels']).tag(sync=True)
    wcs_use_affine_options = List(['Yes', 'No']).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_type = 'pixels'
        self._wcs_fallback_scheme = None
        self._wcs_use_affine = True

    def vue_link_type_selected(self, event):
        if event == 'WCS':
            self._link_type = 'wcs'
        else:
            self._link_type = 'pixels'

    def vue_wcs_fallback_scheme_selected(self, event):
        if event == 'None':
            self._wcs_fallback_scheme = None
        else:
            self._wcs_fallback_scheme = 'pixels'

    def vue_affine_option_selected(self, event):
        if event == 'Yes':
            self._wcs_use_affine = True
        else:
            self._wcs_use_affine = False

    def vue_do_link(self, *args, **kwargs):
        """Run :meth:`jdaviz.configs.imviz.helper.Imviz.link_data`
        with the selected parameters.
        """
        link_image_data(
            self.app, link_type=self._link_type, wcs_fallback_scheme=self._wcs_fallback_scheme,
            wcs_use_affine=self._wcs_use_affine, error_on_fail=False)
