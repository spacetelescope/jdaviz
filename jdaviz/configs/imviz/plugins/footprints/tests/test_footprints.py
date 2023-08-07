import numpy as np

from astropy.nddata import NDData

from jdaviz.core.marks import FootprintOverlay
from jdaviz.configs.imviz.plugins.footprints.preset_regions import _all_apertures


def _get_markers_from_viewer(viewer):
    return [m for m in viewer.figure.marks if isinstance(m, FootprintOverlay)]


def test_user_api(imviz_helper, image_2d_wcs):
    arr = np.ones((10, 10))
    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd)

    plugin = imviz_helper.plugins['Footprints']
    with plugin.as_active():
        for instrument in plugin.instrument.choices:
            plugin.instrument = instrument

            viewer_marks = _get_markers_from_viewer(imviz_helper.default_viewer)
            assert len(viewer_marks) == len(_all_apertures.get(instrument))
