import numpy as np
import os
import pytest
import re

from astropy.io import fits
from astropy.nddata import NDData
import astropy.units as u
from glue.core.edit_subset_mode import AndMode, NewMode
from glue.core.roi import CircularROI, XRangeROI
from regions import Regions, CircleSkyRegion
from specutils import Spectrum1D


class TestExportSubsets():
    """
    Tests for exporting subsets. Currently limited to non-composite spatial
    subsets.
    """

    def test_basic_export_subsets_imviz(self, tmp_path, imviz_helper):

        data = NDData(np.ones((500, 500)) * u.nJy)

        imviz_helper.load_data(data)

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(xc=250,
                                                                     yc=250,
                                                                     radius=100))
        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_format.selected == 'fits'  # default format
        assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial

        export_plugin.export()
        assert os.path.isfile('imviz_export.fits')

        # read exported file back in
        with fits.open('imviz_export.fits') as hdu:
            fits_region = hdu[1].data[0]

        assert fits_region[0] == 'circle'
        assert fits_region[1] == fits_region[2] == 250.0
        assert fits_region[3] == 100.0
        assert fits_region[4] == 0.0

        # now test changing file format
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()
        assert os.path.isfile('imviz_export.reg')

        # read exported file back in
        region = Regions.read('imviz_export.reg')[0]
        assert region.center.x == 250.0
        assert region.center.y == 250.0
        assert region.radius == 100.0

        # changing file name
        export_plugin.filename = 'test'
        export_plugin.export()
        assert os.path.isfile('test.reg')

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape("x not one of ['fits', 'reg'], reverting selection to reg")):  # noqa
            export_plugin.subset_format.selected = 'x'

    def test_not_implemented(self, cubeviz_helper, spectral_cube_wcs):
        """
        Test that trying to export non-supported subsets
        (spectral and composite) produces
        the correct warning message to display in UI).
        """

        data = Spectrum1D(flux=np.ones((500, 500, 2)) * u.nJy,
                          wcs=spectral_cube_wcs)
        cubeviz_helper.load_data(data)

        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=255,
                                                                           yc=255,
                                                                           radius=50))
        cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=200,
                                                                           yc=250,
                                                                           radius=50))

        export_plugin = cubeviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == 'Export for composite subsets not supported.'

        cubeviz_helper.app.session.edit_subset_mode.mode = NewMode
        cubeviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))
        export_plugin.subset.selected = 'Subset 2'

        assert export_plugin.subset_invalid_msg == 'Export for spectral subsets not supported.'

    def test_export_subsets_wcs(self, tmp_path, imviz_helper, spectral_cube_wcs):

        # using cube WCS instead of 2d imaging wcs for consistancy with
        # cubeviz test. accessing just the spatial part of this.
        wcs = spectral_cube_wcs.celestial

        data = NDData(np.ones((500, 500)) * u.nJy, wcs=wcs)

        imviz_helper.load_data(data)  # load data twice so we can link them
        imviz_helper.load_data(data)

        imviz_helper.link_data(link_type='wcs')

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(xc=8,
                                                                     yc=6,
                                                                     radius=.2))

        export_plugin = imviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_invalid_msg == ''  # for non-composite spatial

        # test changing link type results in an output file with a sky region
        export_plugin.filename = 'sky_region'
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()

        assert os.path.isfile('sky_region.reg')

        assert isinstance(Regions.read('sky_region.reg')[0], CircleSkyRegion)

    def test_basic_export_subsets_cubeviz(self, tmp_path, cubeviz_helper, spectral_cube_wcs):

        data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)

        cubeviz_helper.load_data(data)

        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=50,
                                                                           yc=50,
                                                                           radius=10))

        export_plugin = cubeviz_helper.plugins['Export']._obj
        export_plugin.subset.selected = 'Subset 1'

        assert export_plugin.subset_format.selected == 'fits'  # default format

        export_plugin.export()
        assert os.path.isfile('cubeviz_export.fits')

        # read exported file back in
        with fits.open('cubeviz_export.fits') as hdu:
            fits_region = hdu[1].data[0]

        assert fits_region[0] == 'circle'
        assert fits_region[1] == fits_region[2] == 50.0
        assert fits_region[3] == 10.0
        assert fits_region[4] == 0.0

        # now test changing file format
        export_plugin.subset_format.selected = 'reg'
        export_plugin.export()
        assert os.path.isfile('cubeviz_export.reg')

        # read exported file back in
        region = Regions.read('cubeviz_export.reg')[0]
        assert region.center.x == 50.0
        assert region.center.y == 50.0
        assert region.radius == 10.0

        # changing file name
        export_plugin.filename = 'test'
        export_plugin.export()
        assert os.path.isfile('test.reg')

        # test that invalid file extension raises an error
        with pytest.raises(ValueError,
                           match=re.escape("x not one of ['fits', 'reg'], reverting selection to reg")):  # noqa
            export_plugin.subset_format.selected = 'x'

        # test that attempting to save a composite subset raises an error
        cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=25, yc=25, radius=5))
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=20, yc=25, radius=5))

        with pytest.raises(NotImplementedError,
                           match='Subset can not be exported - Export for composite subsets not supported.'):  # noqa
            export_plugin.export()
