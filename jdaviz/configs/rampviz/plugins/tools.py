import os
import numpy as np
from glue.config import viewer_tool
from jdaviz.configs.default.plugins.tools import ProfileFromCube

__all__ = ['RampPerPixel']

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


@viewer_tool
class RampPerPixel(ProfileFromCube):

    # TODO: replace "pixelspectra" graphic with a "pixelramp" equivalent
    icon = os.path.join(ICON_DIR, 'pixelspectra.svg')
    tool_id = 'jdaviz:rampperpixel'
    action_text = 'See ramp at a single pixel'
    tool_tip = (
        'Click on the viewer and see the ramp profile '
        'at that pixel in the integration viewer'
    )

    def on_mouse_move(self, data):
        if data['event'] == 'mouseleave':
            self._mark.visible = False
            self._profile_viewer.reset_limits()
            return

        x = int(np.round(data['domain']['x']))
        y = int(np.round(data['domain']['y']))

        cube_cache = self.viewer.jdaviz_app._jdaviz_helper.cube_cache
        spectrum = cube_cache[list(cube_cache.keys())[0]].data

        if x >= spectrum.shape[0] or x < 0 or y >= spectrum.shape[1] or y < 0:
            self._mark.visible = False
        else:
            y_values = spectrum[x, y, :]
            if np.all(np.isnan(y_values)):
                self._mark.visible = False
                return
            self._mark.update_xy(np.arange(y_values.size), y_values)
            self._mark.visible = True
            self._profile_viewer.reset_limits()
