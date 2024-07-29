from astropy.nddata import NDDataArray

from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.configs.default.plugins.viewers import JdavizProfileView

__all__ = ['RampvizProfileView']


@viewer_registry("rampviz-profile-viewer", label="Profile 1D (Rampviz)")
class RampvizProfileView(JdavizProfileView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = NDDataArray
    _state_cls = FreezableProfileViewerState
    _default_profile_subset_type = 'temporal'
