import warnings

from glue.core import Data
from specutils import Spectrum1D
from specutils.manipulation import spectral_slab
from traitlets import List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin)

__all__ = ['Collapse']


@tray_registry('g-collapse', label="Collapse")
class Collapse(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin, AddResultsMixin):
    template_file = __file__, "collapse.vue"
    funcs = List(['Mean', 'Median', 'Min', 'Max', 'Sum']).tag(sync=True)
    selected_func = Unicode('Sum').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._label_counter = 0

        self.dataset.add_filter('is_image')
        self.add_results.viewer.filters = ['is_image_viewer']

    @observe("dataset_selected", "dataset_items")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += ["collapsed"]
        self.results_label_default = " ".join(label_comps)

    def vue_collapse(self, *args, **kwargs):
        # Collapsing over the spectral axis. Cut out the desired spectral
        # region. Defaults to the entire spectrum.
        cube = self.dataset.get_object(cls=Spectrum1D, statistic=None)
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='No observer defined on WCS')
            spec = spectral_slab(cube, spec_min, spec_max)
            # Spatial-spatial image only.
            collapsed_spec = spec.collapse(self.selected_func.lower(), axis=-1).T  # Quantity

        data = Data()
        data['flux'] = collapsed_spec.value
        data.get_component('flux').units = str(collapsed_spec.unit)

        self.add_results.add_results_from_plugin(data)

        snackbar_message = SnackbarMessage(
            f"Data set '{self.dataset_selected}' collapsed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)
