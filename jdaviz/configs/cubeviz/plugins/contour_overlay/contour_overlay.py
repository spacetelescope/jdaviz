import numpy as np
from bqplot import Figure, LinearScale, Axis, ColorScale
from bqplot_image_gl import ImageGL, Contour
import skimage.measure

from traitlets import List, Unicode, Any, Int, Bool, observe

from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template


__all__ = ['ContourOverlay']


@tray_registry('g-contour-overlay', label="Contour Overlay")
class ContourOverlay(TemplateMixin):
    template = load_template("contour_overlay.vue", __file__).tag(sync=True)

    slice_index = Int().tag(sync=True)
    levels = Any().tag(sync=True)
    visible = Bool().tag(sync=True)

    list_of_viewers = List([]).tag(sync=True)
    overlayed_viewer = Any().tag(sync=True)

    list_of_displays = List([]).tag(sync=True)
    contour_display = Any().tag(sync=True)

    contour_options = List([]).tag(sync=True)
    contour_type = Any().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.list_of_viewers = ["flux-viewer", "uncert-viewer", "mask-viewer"]
        self.list_of_displays = self.data_collection.data
        print(self.list_of_displays)
        self.contour_options = ["sum", "moment map"]

        self.slice_index = 0
        self.visible = True

        self.figure_original_marks = {}
        self.figure_current_marks = {}

        self.figure_overlay_on = None
        self.figure_overlay_of = None

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receieves
        a glue message containing viewer information in the case of the former
        set of events, and updates the available data list displayed to the
        user.

        Notes
        -----
        We do not attempt to parse any data at this point, at it can cause
        visible lag in the application.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        self._viewer_id = self.app._viewer_item_by_reference(
            'spectrum-viewer').get('id')

        # Subsets are global and are not linked to specific viewer instances,
        # so it's not required that we match any specific ids for that case.
        # However, if the msg is not none, check to make sure that it's the
        # viewer we care about.
        if msg is not None and msg.viewer_id != self._viewer_id:
            return

        viewer = self.app.get_viewer('spectrum-viewer')

        # self.list_of_displays = [layer_state.layer.label
        #                  for layer_state in viewer.state.layers]

        self.list_of_displays = [x.label for x in self.data_collection.data]

        # # self.list_of_displays = []
        # for viewer in self.list_of_viewers:
        #     temp_data = self.app.get_data_from_viewer(viewer)
        #     print(temp_data)
        #     self.list_of_displays += temp_data
        #
        #
        # print(self.list_of_displays)


    def vue_contour_overlay(self, *args, **kwargs):
        """
        Runs when the `apply` button is hit.
        """
        self.figure_overlay_on = self.app.get_viewer(self.overlayed_viewer)
        # self.figure_overlay_of = self.app.get_viewer(self.contour_display)

        if self.figure_overlay_on in self.figure_original_marks \
                and self.figure_original_marks[self.figure_overlay_on] is None:
            self.figure_original_marks[self.figure_overlay_on] = self.figure_overlay_on.figure.marks
        elif self.figure_overlay_on not in self.figure_original_marks:
            self.figure_original_marks[self.figure_overlay_on] = self.figure_overlay_on.figure.marks
        elif self.figure_overlay_on in self.figure_original_marks \
            and self.figure_original_marks[self.figure_overlay_on] is not None:
            self.figure_overlay_on.figure.marks = self.figure_original_marks[self.figure_overlay_on]

        self.slice_index = self.figure_overlay_on.state.slices[0]

        #data = self.app.data_collection[self.figure_overlay_of.state.reference_data.label].get_object()
        data = self.app.data_collection[self.contour_display].get_object()
        print(data)
        data_at_slice = data.unmasked_data[self.slice_index, :, :].value
        print(data_at_slice)

        max_level = np.max(data_at_slice)
        if self.levels is None:
            contour_levels = [max_level/10000., max_level/1000., max_level/100., max_level/10.]
        else:
            contour_levels = [float(x) for x in self.levels.split(",")]

        scale_x = LinearScale(min=0, max=1)
        scale_y = LinearScale(min=0, max=1)
        # scales = {'x': scale_x, 'y': scale_y}
        # axis_x = Axis(scale=scale_x, label='x')
        # axis_y = Axis(scale=scale_y, label='y', orientation='vertical')
        scales_image = {'x': scale_x, 'y': scale_y,
                        'image': ColorScale(min=np.min(data_at_slice).item(), max=np.max(data_at_slice).item())}

        # figure = Figure(scales=scales, axes=[axis_x, axis_y])
        image = ImageGL(image=data_at_slice, scales=scales_image)



        contour_list = []
        for contour_level in contour_levels:
            contours = skimage.measure.find_contours(data_at_slice, contour_level)
            contour_shape = [k / data_at_slice.shape for k in contours]

            contour = Contour(contour_lines=[contour_shape], color="orange", scales=scales_image, label_steps=200)

            self.figure_overlay_on.figure.marks = self.figure_overlay_on.figure.marks + [contour]
        print(contour_levels)



        #contour = Contour(contour_lines=[contour_list], color="orange", scales=scales_image, label_steps=200)
        ##contour = Contour(level=contour_levels, scales=scales_image, color="blue", label_steps=200)
        #self.figure_current_marks[self.figure_overlay_on] = self.figure_overlay_on.figure.marks + [contour_list]

        #self.figure_overlay_on.figure.marks = self.figure_overlay_on.figure.marks + [contour_list]

        self.visible = True

        snackbar_message = SnackbarMessage(
            f"Contour overlay set successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)


    @observe("visible")
    def _observe_visible(self, event):
        if event["new"] and hasattr(self, "figure_current_marks"):
            self.app.get_viewer(self.overlayed_viewer).figure.marks = self.figure_current_marks[self.figure_overlay_on]
        elif event["new"]==False and hasattr(self, "figure_original_marks"):
            self.app.get_viewer(self.overlayed_viewer).figure.marks = self.figure_original_marks[self.figure_overlay_on]
