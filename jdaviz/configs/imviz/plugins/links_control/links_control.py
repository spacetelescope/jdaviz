from traitlets import List, Unicode, Bool, observe

from glue.core.message import DataCollectionAddMessage

from jdaviz.configs.imviz.helper import link_image_data
from jdaviz.core.events import LinkUpdatedMessage, ExitBatchLoadMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SelectPluginComponent
from jdaviz.core.user_api import PluginUserApi

__all__ = ['LinksControl']


@tray_registry('imviz-links-control', label="Links Control")
class LinksControl(PluginTemplateMixin):
    """
    See the :ref:`Links Control Plugin Documentation <imviz-link-control>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``link_type`` (`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``wcs_use_affine``
    """
    template_file = __file__, "links_control.vue"

    link_type_items = List().tag(sync=True)
    link_type_selected = Unicode().tag(sync=True)
    wcs_use_fallback = Bool(True).tag(sync=True)
    wcs_use_affine = Bool(True).tag(sync=True)

    need_clear_markers = Bool(False).tag(sync=True)
    linking_in_progress = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cancel_revert = {}

        self.link_type = SelectPluginComponent(self,
                                               items='link_type_items',
                                               selected='link_type_selected',
                                               manual_options=['Pixels', 'WCS'])

        self.hub.subscribe(self, LinkUpdatedMessage,
                           handler=self._on_link_updated)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_new_app_data)

        self.hub.subscribe(self, ExitBatchLoadMessage,
                           handler=self._on_new_app_data)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('link_type', 'wcs_use_affine'))

    def _on_link_updated(self, msg):
        self.link_type.selected = {'pixels': 'Pixels', 'wcs': 'WCS'}[msg.link_type]
        self.linking_in_progress = True
        self.wcs_use_fallback = msg.wcs_use_fallback
        self.wcs_use_affine = msg.wcs_use_affine

    def _link_image_data(self):
        link_image_data(
            self.app,
            link_type=self.link_type.selected.lower(),
            wcs_fallback_scheme='pixels' if self.wcs_use_fallback else None,
            wcs_use_affine=self.wcs_use_affine,
            error_on_fail=False,
            update_plugin=False)

    def _on_new_app_data(self, msg):
        if self.app._jdaviz_helper._in_batch_load > 0:
            return
        if isinstance(msg, DataCollectionAddMessage):
            components = [str(comp) for comp in msg.data.main_components]
            if "ra" in components or "Lon" in components:
                # linking currently removes any markers, so we want to skip
                # linking immediately after new markers are added
                # (see imviz.helper.link_image_data).
                # Eventually we'll probably want to support linking WITH markers,
                # at which point this if-statement should be removed.
                return
        self._link_image_data()

    @observe('link_type_selected', 'wcs_use_fallback', 'wcs_use_affine')
    def _update_link(self, msg={}):
        """Run :func:`jdaviz.configs.imviz.helper.link_image_data`
        with the selected parameters.
        """
        if not hasattr(self, 'link_type'):
            # could happen before plugin is fully initialized
            return

        if msg.get('name', None) == 'wcs_use_affine' and self.link_type.selected == 'Pixels':
            # approximation doesn't apply, avoid updating when not necessary!
            return

        if self.linking_in_progress:
            return

        for viewer in self.app._viewer_store.values():
            if len(viewer._marktags):
                if self.need_clear_markers:
                    viewer.remove_markers()
                else:
                    # show an overlay requiring the user to either clear markers first or cancel
                    # if the user clicks to clear, this method will be retriggered and the previous
                    # if statement will be triggered
                    self.cancel_revert[msg.get('name')] = msg.get('old')
                    self.need_clear_markers = True
                    return

        self.need_clear_markers = False
        self.linking_in_progress = True

        if self.link_type.selected == 'Pixels':
            # reset wcs_use_affine to be True
            self.wcs_use_affine = True

        self._link_image_data()

        self.linking_in_progress = False

    def vue_clear_markers_and_link(self, *args):
        self._update_link()

    def vue_cancel_link(self, *args):
        self.linking_in_progress = True  # just set the traitlet, don't actually link
        for k, v in self.cancel_revert.items():
            setattr(self, k, v)
        self.cancel_revert = {}
        self.need_clear_markers = False
        self.linking_in_progress = False
