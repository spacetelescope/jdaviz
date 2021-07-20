from glue.core.roi import CircularROI, EllipticalROI, RectangularROI
from glue.core.subset import Subset
from glue.core.message import SubsetUpdateMessage, SubsetDeleteMessage
from traitlets import Bool, Float, List

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['SubsetControl']


@tray_registry('imviz-subset-control', label="Subset Control")
class SubsetControl(TemplateMixin):
    template = load_template("subset_control.vue", __file__).tag(sync=True)

    subset_items = List([]).tag(sync=True)
    new_subset_angle = Float(default=0).tag(sync=True)
    new_subset_x = Float().tag(sync=True)
    new_subset_y = Float().tag(sync=True)
    has_angle = Bool().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_subset_label = ''
        self._all_subsets = {}

        # NOTE: Subscribing to SubsetCreateMessage breaks Subset interactive creation.
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_subset_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_subset_changed())

    def get_subset_rois(self):
        """Get a list of all current Subset ROI objects."""
        # Even though Subset is global, still need to access it from viewer.
        viewer = self.app.get_viewer('viewer-1')
        rois = {}
        for layer_state in viewer.state.layers:
            if hasattr(layer_state, 'layer') and isinstance(layer_state.layer, Subset):
                rois[layer_state.layer.label] = layer_state.layer.subset_state.roi
        return rois

    def _on_viewer_subset_changed(self):
        """Callback method for when a subset is updated or deleted."""
        self._all_subsets = self.get_subset_rois()
        self.subset_items = sorted(self._all_subsets.keys())

    def vue_subset_selected(self, event):
        self._selected_subset_label = event
        cur_roi = self._all_subsets[self._selected_subset_label]
        self.has_angle = has_roi_angle(cur_roi)

        # https://github.com/glue-viz/glue/issues/2207
        if isinstance(cur_roi, (CircularROI, EllipticalROI)):
            # NOTE: vuejs complains about float32 if float is not cast explicitly.
            self.new_subset_x = float(cur_roi.xc)
            self.new_subset_y = float(cur_roi.yc)
        else:
            cur_pos = cur_roi.center()
            self.new_subset_x = cur_pos[0]
            self.new_subset_y = cur_pos[1]

        # TODO: Need upstream fix to access angle property.
        # TODO: Do we care about setting of this field when Subset has no angle property?
        if self.has_angle:
            self.new_subset_angle = 42
        else:
            self.new_subset_angle = 0

    def vue_update_subset(self, event):
        # TODO: Does not work! How to actually move it?
        # TODO: Using echo.delay_callback breaks the call too.
        cur_roi = self._all_subsets[self._selected_subset_label]
        try:
            cur_roi.move_to(self.new_subset_x, self.new_subset_y)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"{repr(e)}", color='error', sender=self))

        if has_roi_angle(cur_roi):
            # TODO: Need upstream fix to access angle property.
            pass

        # TODO: Debugging only. Remove me.
        self.hub.broadcast(SnackbarMessage(f"{event}", color='info', sender=self))


def has_roi_angle(roi):
    """Determine whether ROI has angle property."""
    has_angle = False
    if isinstance(roi, (EllipticalROI, RectangularROI)):
        has_angle = True
    return has_angle
