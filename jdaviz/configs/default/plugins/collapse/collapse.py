import warnings

from glue.core import Data
from specutils import Spectrum1D
from specutils.manipulation import spectral_slab
from traitlets import List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Collapse']


@tray_registry('g-collapse', label="Collapse", viewer_requirements='spectrum')
class Collapse(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Collapse Plugin Documentation <collapse>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the line, or ``Entire Spectrum``.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`collapse`
    """
    template_file = __file__, "collapse.vue"
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)

    def __init__(self, *args, **kwargs):

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )

        super().__init__(*args, **kwargs)

        self._label_counter = 0

        self.function = SelectPluginComponent(self,
                                              items='function_items',
                                              selected='function_selected',
                                              manual_options=['Mean', 'Median', 'Min', 'Max', 'Sum'])  # noqa

        self.dataset.add_filter('is_cube')
        self.add_results.viewer.filters = ['is_image_viewer']

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'function', 'spectral_subset',
                                           'add_results', 'collapse'))

    @observe("dataset_selected", "dataset_items")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += ["collapsed"]
        self.results_label_default = " ".join(label_comps)

    def collapse(self, add_data=True):
        """
        Collapse over the spectral axis.

        Parameters
        ----------
        add_data : bool
            Whether to load the resulting data back into the application according to
            ``add_results``.
        """
        # Collapsing over the spectral axis. Cut out the desired spectral
        # region. Defaults to the entire spectrum.
        cube = self.dataset.get_object(cls=Spectrum1D, statistic=None)
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='No observer defined on WCS')
            spec = spectral_slab(cube, spec_min, spec_max)
            # Spatial-spatial image only.
            collapsed_spec = spec.collapse(self.function_selected.lower(), axis=-1).T  # Quantity

        if add_data:
            data = Data()
            data['flux'] = collapsed_spec.value
            data.get_component('flux').units = str(collapsed_spec.unit)

            self.add_results.add_results_from_plugin(data)

            snackbar_message = SnackbarMessage(
                f"Data set '{self.dataset_selected}' collapsed successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        return collapsed_spec

    def vue_collapse(self, *args, **kwargs):
        self.collapse(add_data=True)
