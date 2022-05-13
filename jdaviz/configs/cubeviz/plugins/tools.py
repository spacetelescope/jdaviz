import time
import os

from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool
from glue.core.link_helpers import LinkSame
from echo import delay_callback
from specutils import Spectrum1D

from jdaviz.core.events import SliceSelectWavelengthMessage, SliceToolStateMessage
from jdaviz.core.marks import SelectedPixel

__all__ = ['SelectSlice', 'SpectrumPerSpaxel']

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


@viewer_tool
class SelectSlice(CheckableTool):
    icon = os.path.join(ICON_DIR, 'slice.svg')
    tool_id = 'jdaviz:selectslice'
    action_text = 'Select cube slice (spectral axis)'
    tool_tip = 'Select cube slice (spectral axis)'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['dragmove', 'click'])
        msg = SliceToolStateMessage({'active': True}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        msg = SliceToolStateMessage({'active': False}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def on_mouse_event(self, data):
        if (time.time() - self._time_last) <= 0.2:
            # throttle to 200ms
            return

        msg = SliceSelectWavelengthMessage(wavelength=data['domain']['x'], sender=self)
        self.viewer.session.hub.broadcast(msg)

        self._time_last = time.time()


@viewer_tool
class SpectrumPerSpaxel(CheckableTool):

    icon = os.path.join(ICON_DIR, 'pixelspectra.svg')
    tool_id = 'jdaviz:spectrumperspaxel'
    action_text = 'See spectrum at a single spaxel'
    tool_tip = 'Click on the viewer and see the spectrum at that spaxel in the spectrum viewer'

    def __init__(self, viewer, **kwargs):
        self.old_y_min = 0
        self.old_y_max = 0
        self.spectrum_viewer = None

        # #b515d1 is magenta
        self.colors = ['#b515d1']
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])
        self.spectrum_viewer = self.viewer.jdaviz_app.get_viewer_by_id("cubeviz-3")
        self.old_y_min, self.old_y_max = (self.spectrum_viewer.state.y_min,
                                          self.spectrum_viewer.state.y_max)

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        with delay_callback(self.spectrum_viewer.state, 'y_min', 'y_max'):
            self.spectrum_viewer.state.y_min, self.spectrum_viewer.state.y_max = (self.old_y_min,
                                                                                  self.old_y_max)
        self.remove_highlight_on_pixel()

    def on_mouse_event(self, data):
        event = data['event']

        if event == 'click':
            event_x = data['domain']['x']
            event_y = data['domain']['y']

            x = round(event_x)
            y = round(event_y)

            self.remove_highlight_on_pixel()
            self.highlight_pixel(x, y)

            new_y_min = 0
            new_y_max = 0

            # Spectrum is created for each active layer in the viewer
            for data in self.viewer.data():
                if len(data.shape) != 3:
                    return

                cube = data.get_object(cls=Spectrum1D, statistic=None)
                if x > cube.shape[0] or y > cube.shape[1] or x < 0 or y < 0:
                    return

                spec = Spectrum1D(flux=cube.flux[x][y], spectral_axis=cube.spectral_axis)
                label = f"{data.label}_at_pixel"

                # Remove data from viewer, re-add data to app, and then add data
                # back to spectrum viewer
                self.viewer.jdaviz_app.remove_data_from_viewer("spectrum-viewer", label)
                self.viewer.jdaviz_app.add_data(spec, label)
                self.viewer.jdaviz_app.add_data_to_viewer("spectrum-viewer",
                                                          label,
                                                          clear_other_data=False)

                # Add meta data for reference data and pixel
                dc = self.viewer.session.data_collection
                dc[label].meta["reference_data"] = data.label
                dc[label].meta["created_from_pixel"] = f"({x}, {y})"

                # Set color of spectrum to magenta to not conflict with subset colors
                self.spectrum_viewer.figure.marks[-1].colors = self.colors

                # Link newly created spectrum to reference data
                ref_cube = self.spectrum_viewer.state.reference_data
                new_spec = dc[label]
                self.link_data(ref_cube, new_spec)

                # Set y limits based on the new spectrum or spectra being created
                if max(spec.flux.value) > new_y_max:
                    new_y_max = max(spec.flux.value)
                if min(spec.flux.value) < new_y_min:
                    new_y_min = min(spec.flux.value)

            with delay_callback(self.spectrum_viewer.state, 'y_min', 'y_max'):
                self.spectrum_viewer.state.y_min, self.spectrum_viewer.state.y_max = (new_y_min,
                                                                                      new_y_max)

    def link_data(self, data1, data2):
        if data1.label == data2.label:
            return
        world1 = data1.world_component_ids
        world2 = data2.world_component_ids
        if len(world1) == 3 and len(world2) == 1:
            links = [LinkSame(world1[2], world2[0])]
        elif len(world1) == 1 and len(world2) == 1:
            links = [LinkSame(world1[0], world2[0])]
        else:
            return

        self.viewer.session.data_collection.add_link(links)

    def highlight_pixel(self, x, y):
        # Creates a box that outlines the pixel at coordinate (x, y)
        x_coords = [x - 0.5, x + 0.5, x + 0.5, x - 0.5]
        y_coords = [y - 0.5, y - 0.5, y + 0.5, y + 0.5]

        # Create LinearScale that is the same size as the image viewer
        scales = {'x': self.viewer.figure.interaction.x_scale,
                  'y': self.viewer.figure.interaction.y_scale}
        highlight = SelectedPixel(x=x_coords, y=y_coords, scales=scales,
                                  fill='none', colors=self.colors, stroke_width=2,
                                  close_path=True)
        self.viewer.figure.marks = self.viewer.figure.marks + [highlight]

    def remove_highlight_on_pixel(self):
        self.viewer.figure.marks = [x for x in self.viewer.figure.marks
                                    if not isinstance(x, SelectedPixel)]
