import numpy as np
import time
from glue.core.data import Data
from traitlets import Bool, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        AutoTextFieldMixin)
from jdaviz.core.user_api import PluginUserApi

try:
    from reproject import reproject_interp
    from reproject.mosaicking import find_optimal_celestial_wcs
except ImportError:
    HAS_REPROJECT = False
else:
    HAS_REPROJECT = True

__all__ = ['Reproject']


@tray_registry('imviz-reproject', label="Reproject")
class Reproject(PluginTemplateMixin, DatasetSelectMixin, AutoTextFieldMixin):
    template_file = __file__, "reproject.vue"

    reproject_in_progress = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not HAS_REPROJECT:
            self.disabled_msg = 'Please install reproject and restart Jdaviz to use this plugin'
            return

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'label', 'reproject'))

    @observe("dataset_selected")
    def _set_default_results_label(self, event={}):
        '''Generate a label and set the results field to that value'''
        self.label_default = f"{self.dataset_selected} (reprojected)"

    @observe('label')
    def _label_changed(self, event={}):
        if not len(self.label.strip()):
            # strip will raise the same error for a label of all spaces
            self.label_invalid_msg = 'label must be provided'
            return
        if self.label.strip() in self.data_collection:
            self.label_invalid_msg = 'label already in use'
            return
        self.label_invalid_msg = ''

    def reproject(self):
        """
        Reproject ``dataset`` so that North is up in a new entry labeled ``label`` and set as the
        reference image.
        """
        if (not HAS_REPROJECT or self.dataset_selected not in self.data_collection
                or self.reproject_in_progress):
            return

        import reproject

        data = self.data_collection[self.dataset_selected]
        wcs_in = data.coords
        if wcs_in is None:
            return

        viewer_reference = f"{self.app.config}-0"
        self.reproject_in_progress = True
        t_start = time.time()
        try:
            if self.label in self.app.data_collection.labels:
                raise ValueError(
                    f'{self.label} is already used, choose another label name.')

            # Find WCS where North is pointing up.
            wcs_out, shape_out = find_optimal_celestial_wcs([(data.shape, wcs_in)], frame='icrs')

            # Reproject image to new WCS.
            comp = data.get_component(data.main_components[0])
            new_arr = reproject_interp((comp.data, wcs_in), wcs_out, shape_out=shape_out,
                                       return_footprint=False)

            # Stuff it back into Imviz and show in default viewer.
            # We don't want to inherit input metadata because it might have wrong (unrotated)
            # WCS info in the header metadata.
            new_data = Data(label=self.label,
                            coords=wcs_out,
                            data=np.nan_to_num(new_arr, copy=False))
            new_data.meta.update({'orig_label': data.label,
                                  'reproject_version': reproject.__version__})
            self.app.add_data(new_data, self.label)
            self.app.add_data_to_viewer(viewer_reference, self.label)

            # We unload the unrotated image from default viewer.
            # Only do this after we add the reprojected data to avoid JSON warning.
            self.app.remove_data_from_viewer(viewer_reference, data.label)

            # Make the reprojected image the reference data for the default viewer.
            viewer = self.app.get_viewer(viewer_reference)
            viewer.state.reference_data = new_data

        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Failed to reproject {data.label}: {repr(e)}",
                color='error', sender=self))

        else:
            t_end = time.time()
            self.hub.broadcast(SnackbarMessage(
                f"Reprojection of {data.label} took {t_end - t_start:.1f} seconds.",
                color='info', sender=self))

        finally:
            self.reproject_in_progress = False

    def vue_do_reproject(self, *args, **kwargs):
        self.reproject()
