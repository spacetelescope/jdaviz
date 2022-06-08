import numpy as np
from astropy.nddata import NDData
from traitlets import Any, Bool, observe

from jdaviz.configs.imviz.helper import link_image_data
from jdaviz.configs.imviz.plugins.parsers import _nddata_to_glue_data
from jdaviz.configs.imviz.wcs_utils import generate_rotated_wcs
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin, DatasetSelectMixin

__all__ = ['RotateImageSimple']


@tray_registry('imviz-rotate-image', label="Simple Image Rotation")
class RotateImageSimple(TemplateMixin, ViewerSelectMixin, DatasetSelectMixin):
    template_file = __file__, "rotate_image.vue"

    rotate_mode_on = Bool(False).tag(sync=True)
    angle = Any(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._theta = 0  # degrees, clockwise

        # Dummy array to go with the rotated WCS, modified as needed later.
        ndd = NDData(np.zeros((2, 2), dtype=np.uint8), wcs=generate_rotated_wcs(0),
                     meta={'Plugin': 'Simple Image Rotation'})
        for cur_data, cur_label in _nddata_to_glue_data(ndd, '_simple_rotated_wcs_ref'):
            self._data_ref = cur_data
            self._data_ref_label = cur_label
            break  # Just the DATA

    def _update_all_viewers(self):
        for viewer in self.app._viewer_store.values():
            viewer.update()  # Force viewer to update.

    @observe('rotate_mode_on')
    def vue_toggle_on_off(self, *args, **kwargs):
        # It is hard to keep track what the previous reference data was or
        # if it is still valid, so just brute force here.
        if not self.rotate_mode_on:
            for vid in self.app.get_viewer_ids():
                # This is silent no-op if it is not in that viewer.
                try:
                    self.app.remove_data_from_viewer(vid, self._data_ref_label)
                except Exception:  # nosec B110
                    pass

    def vue_rotate_image(self, *args, **kwargs):
        # We only grab the value here to avoid constantly updating as
        # user is still entering or updating the value.
        try:
            self._theta = float(self.angle)
        except Exception:
            return

        w_data = self.dataset.selected_dc_item.coords
        if w_data is None:  # Nothing to do
            return

        try:
            # Adjust the fake WCS to data with desired orientation.
            w_in = generate_rotated_wcs(self._theta)

            # TODO: How to make this more robust?
            # Match with selected data.
            w_shape = self.dataset.selected_dc_item.shape
            sky0 = w_data.pixel_to_world(0, 0)
            sky1 = w_data.pixel_to_world(w_shape[1] * 0.5, w_shape[0] * 0.5)
            avg_cdelt = (abs(sky1.ra.deg - sky0.ra.deg) + abs(sky1.dec.deg - sky0.dec.deg)) * 0.5
            w_in.wcs.crval = np.array([sky1.ra.deg, sky1.dec.deg])
            w_in.wcs.cdelt = np.array([-avg_cdelt, avg_cdelt])
            w_in.wcs.set()

            # Add it into data collection if not already there.
            if self._data_ref_label not in self.app.data_collection.labels:
                self.app.add_data(self._data_ref, data_label=self._data_ref_label,
                                  notify_done=False)

            # Update the WCS.
            self.app.data_collection[self._data_ref_label].coords = w_in

            # Force link by WCS if not already. Otherwise, no point in rotating WCS.
            # Default settings is enough since we already said distortions are ignored.
            link_image_data(self.app, link_type='wcs')

            # Make it a reference.
            self.app.add_data_to_viewer(self.viewer_selected, self._data_ref_label,
                                        clear_other_data=False)
            viewer = self.app.get_viewer(self.viewer_selected)
            if viewer.state.reference_data.label != self._data_ref_label:
                viewer.state.reference_data = self.app.data_collection[self._data_ref_label]

            # Force all viewers to update.
            self._update_all_viewers()
        except Exception as err:
            self.hub.broadcast(SnackbarMessage(
                f"Image rotation failed: {repr(err)}", color='error', sender=self))
