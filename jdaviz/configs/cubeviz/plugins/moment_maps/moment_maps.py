import os

from astropy import units as u
from astropy.nddata import CCDData
from glue.core.link_helpers import LinkSame

from traitlets import Unicode, Bool, observe
from specutils import Spectrum1D, manipulation, analysis

from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin)

__all__ = ['MomentMap']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('cubeviz-moment-maps', label="Moment Maps")
class MomentMap(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin,
                AddResultsMixin):
    template_file = __file__, "moment_maps.vue"

    n_moment = IntHandleEmpty(0).tag(sync=True)
    filename = Unicode().tag(sync=True)
    moment_available = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.moment = None

        self.dataset.add_filter('is_image')
        self.add_results.viewer.filters = ['is_image_viewer']

    @observe("dataset_selected", "dataset_items", "n_moment")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += [f"moment {self.n_moment}"]
        self.results_label_default = " ".join(label_comps)

    def vue_calculate_moment(self, *args):
        # Retrieve the data cube and slice out desired region, if specified
        cube = self.dataset.get_object(cls=Spectrum1D, statistic=None)
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)
        slab = manipulation.spectral_slab(cube, spec_min, spec_max)

        # Calculate the moment and convert to CCDData to add to the viewers
        try:
            n_moment = int(self.n_moment)
            if n_moment < 0:
                raise ValueError("Moment must be a positive integer")
        except ValueError:
            raise ValueError("Moment must be a positive integer")
        # Need transpose to align JWST mirror shape. Not sure why.
        self.moment = CCDData(analysis.moment(slab, order=n_moment).T)

        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"moment{n_moment}_{fname_label}.fits"

        self.add_results.add_results_from_plugin(self.moment)
        self._link_moment_data()

        self.moment_available = True

        msg = SnackbarMessage("{} added to data collection".format(self.results_label),
                              sender=self, color="success")
        self.hub.broadcast(msg)

    def vue_save_as_fits(self, *args):
        if self.moment is None or not self.filename:  # pragma: no cover
            return

        self.moment.write(self.filename)
        # Let the user know where we saved the file.
        self.hub.broadcast(SnackbarMessage(
            f"Moment map saved to {os.path.abspath(self.filename)}", sender=self, color="success"))

    def _link_moment_data(self):
        new_len = len(self.app.data_collection)

        # Can't link if there's no world_component_ids
        pc_new = self.app.data_collection[-1].pixel_component_ids

        # Link to the first dataset with compatible coordinates
        for i in range(new_len - 1):
            pc_old = self.app.data_collection[i].pixel_component_ids
            # If data_collection[i] is also from the moment map
            if self.app.data_collection[i].meta.get("Plugin", None) == self.__class__.__name__:
                links = [LinkSame(pc_old[0], pc_new[0]),
                         LinkSame(pc_old[1], pc_new[1])]

            # Link moment map to cube (pc_old)
            else:
                links = [LinkSame(pc_old[1], pc_new[0]),
                         LinkSame(pc_old[2], pc_new[1])]

            self.app.data_collection.add_link(links)

            break
