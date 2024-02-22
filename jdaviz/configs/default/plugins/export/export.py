from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, SelectPluginComponent,
                                        ViewerSelectMixin, DatasetMultiSelectMixin,
                                        MultiselectMixin)
from jdaviz.core.user_api import PluginUserApi


__all__ = ['Export']


@tray_registry('export', label="Export")
class Export(PluginTemplateMixin, ViewerSelectMixin, DatasetMultiSelectMixin, MultiselectMixin):
    """
    See the :ref:`Export Plugin Documentation <export>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """
    template_file = __file__, "export.vue"

    # feature flag for cone support
    dev_dataset_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_multi_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_table_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring

    table_items = List().tag(sync=True)
    table_selected = Any().tag(sync=True)

    viewer_format_items = List().tag(sync=True)
    viewer_format_selected = Unicode().tag(sync=True)

    # For Cubeviz movie.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.table = SelectPluginComponent(self,
                                           items='table_items',
                                           selected='table_selected',
                                           multiselect='multiselect',
                                           manual_options=['table-tst1', 'table-tst2'])

        self.viewer_format = SelectPluginComponent(self,
                                                   items='viewer_format_items',
                                                   selected='viewer_format_selected',
                                                   manual_options=['png', 'svg'])

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the movie in python would save on the server, not
            # on the user's machine, so movie support in cubeviz should be disabled
            self.movie_enabled = False

    @property
    def user_api(self):
        # TODO: backwards compat for save_movie, etc
        expose = ['viewer', 'viewer_format']

        if self.dev_dataset_support:
            expose += ['dataset']
        if self.dev_multi_support:
            expose += ['multiselect']
        if self.dev_table_support:
            expose += ['table']

        return PluginUserApi(self, expose=expose)

    @observe('multiselect', 'viewer_multiselect')
    def _sync_multiselect_traitlets(self, event):
        # ViewerSelectMixin brings viewer_multiselect, but we want a single traitlet to control
        # all select inputs, so we'll keep them synced here and only expose multiselect through
        # the user API
        self.multiselect = event.get('new')
        self.viewer_multiselect = event.get('new')
        if not self.multiselect:
            # default to just a single viewer
            self._sync_singleselect({'name': 'viewer', 'new': self.viewer_selected})

    @observe('viewer_selected', 'dataset_selected', 'table_selected')
    def _sync_singleselect(self, event):
        if not hasattr(self, 'dataset') or not hasattr(self, 'viewer'):
            # plugin not fully intialized
            return
        # if multiselect is not enabled, only allow a single selection across all select components
        if self.multiselect:
            return
        if event.get('new') in ('', []):
            return
        name = event.get('name')
        for attr in ('viewer_selected', 'dataset_selected', 'table_selected'):
            if name != attr:
                setattr(self, attr, '')
