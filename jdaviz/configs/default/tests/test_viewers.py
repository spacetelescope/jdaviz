"""
Tests for JdavizViewerMixin ROI edit-detection helpers and the
``apply_roi`` override that lets users resize/move subsets in-place
in the deconfigged configuration.
"""

import pytest
from glue.core.roi import (
    CircularAnnulusROI,
    CircularROI,
    EllipticalROI,
    RectangularROI,
    XRangeROI,
)
from glue.core.subset import RangeSubsetState
from glue_jupyter.bqplot.common.tools import TrueCircularROI

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin


class TestROIEdits:
    """
    Unit tests for all types of ROI edits as well as
    app testing.
    """
    @pytest.fixture(autouse=True)
    def setup_class(self, deconfigged_helper, image_hdu_wcs, spectrum1d):
        self.JVM = JdavizViewerMixin
        deconfigged_helper.load(image_hdu_wcs, format='Image')
        deconfigged_helper.load(spectrum1d, format='1D Spectrum')

        self.app = deconfigged_helper
        self.image_viewer = deconfigged_helper.app.get_viewer('Image')
        self.spectrum_viewer = deconfigged_helper.app.get_viewer('1D Spectrum')
        print(dir(self.spectrum_viewer))

    def _subset_count(self):
        return len(self.app.plugins['Subset Tools'].get_regions())

    # def _active_subset_state(self):
    #     esm = self.viewer.session.edit_subset_mode
    #     if esm.edit_subset:
    #         return esm.edit_subset[0].subset_state
    #     return None

    # ---------------------------------------------------------------------------
    # _is_circular_edit
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        ('delta_xc', 'delta_yc', 'delta_r', 'validity'),
        [(0, 0, 3, True),  # resize same center
         (2, 0, 3, True),  # resize center within radius
         (40, 40, 0, True),  # move same radius
         (40, 40, 3, False)]  # new draw (move and resize)
    )
    def test_circular_roi_edit(self, delta_xc, delta_yc, delta_r, validity):

        # Test with zero initial radius, always False since any change would be a new draw
        old = CircularROI(xc=10, yc=10, radius=0)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert not self.JVM._is_circular_edit(old, new)
        assert not self.JVM._is_roi_edit(self.JVM, old, new)

        # Check subclass
        old = TrueCircularROI(xc=10, yc=10, radius=5)
        new = TrueCircularROI(xc=old.xc + delta_xc,
                              yc=old.yc + delta_yc,
                              radius=old.radius + delta_r)
        assert self.JVM._is_circular_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert self.JVM._is_circular_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test in app behavior: resize, move, and new draw.
        # Draw initial roi and verify count
        self.image_viewer.apply_roi(old)
        assert self._subset_count() == 1

        self.image_viewer.apply_roi(new)
        assert self._subset_count() == (1 if validity else 2)

        different_roi = CircularROI(xc=100, yc=100, radius=2)
        self.image_viewer.apply_roi(different_roi)
        assert self._subset_count() == (2 if validity else 3)

    # ---------------------------------------------------------------------------
    # _is_annulus_edit AND _is_elliptical_edit (same logic for both, just different parameters)
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ('delta_xc', 'delta_yc', 'delta_ixr', 'delta_oyr', 'validity'),
        [(0, 0, 1, 2, True),  # resize same center
         (40, 40, 0, 0, True),  # move same radii
         (40, 40, 2, 4, False),  # new draw (move and resize)
         (40, 40, 1, 0, False),  # different inner/x radius
         (40, 40, 0, 2, False)]  # different outer/y radius
    )
    def test_annulus_elliptical_roi_edit(self, delta_xc, delta_yc, delta_ixr, delta_oyr, validity):
        # Test with zero initial outer radius and smaller initial outer radius,
        # always False since any change would be a new draw
        for old_ir, old_or in ((0, 0), (1, 0)):
            old = CircularAnnulusROI(xc=10, yc=10, inner_radius=old_ir, outer_radius=old_or)
            new = CircularAnnulusROI(xc=old.xc + delta_xc,
                                     yc=old.yc + delta_yc,
                                     inner_radius=old.inner_radius + delta_ixr,
                                     outer_radius=old.outer_radius + delta_oyr)
            assert not self.JVM._is_annulus_edit(old, new)
            assert not self.JVM._is_roi_edit(self.JVM, old, new)

        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=old.xc + delta_xc,
                                 yc=old.yc + delta_yc,
                                 inner_radius=old.inner_radius + delta_ixr,
                                 outer_radius=old.outer_radius + delta_oyr)
        assert self.JVM._is_annulus_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test in app behavior: resize, move, and new draw.
        # Draw initial roi and verify count
        # self.image_viewer.apply_roi(old)
        # assert self._subset_count() == 1
        #
        # self.image_viewer.apply_roi(new)
        # assert self._subset_count() == (1 if validity else 2)
        #
        # different_roi = CircularAnnulusROI(xc=100, yc=100, inner_radius=2, outer_radius=4)
        # self.image_viewer.apply_roi(different_roi)
        # assert self._subset_count() == (2 if validity else 3)

        # ---------------------------------------------------------------------------
        # _is_elliptical_edit
        # ---------------------------------------------------------------------------
        # Test with zero initial x/y radius
        for i, j in ((0, 1), (1, 0)):
            old = EllipticalROI(xc=10, yc=10, radius_x=i, radius_y=j)
            new = EllipticalROI(xc=old.xc + delta_xc,
                                yc=old.yc + delta_yc,
                                radius_x=old.radius_x + delta_ixr,
                                radius_y=old.radius_y + delta_oyr)
            assert not self.JVM._is_elliptical_edit(old, new)
            assert not self.JVM._is_roi_edit(self.JVM, old, new)

        old = EllipticalROI(xc=10, yc=10, radius_x=3, radius_y=6)
        new = EllipticalROI(xc=old.xc + delta_xc,
                            yc=old.yc + delta_yc,
                            radius_x=old.radius_x + delta_ixr,
                            radius_y=old.radius_y + delta_oyr)
        assert self.JVM._is_elliptical_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test in app behavior: resize, move, and new draw.
        # Draw initial roi and verify count
        # annulus_count = self._subset_count()
        # self.image_viewer.apply_roi(old)
        # assert self._subset_count() == annulus_count + 1
        #
        # self.image_viewer.apply_roi(new)
        # assert self._subset_count() == (annulus_count + (1 if validity else 2))
        #
        # different_roi = EllipticalROI(xc=100, yc=100, radius_x=2, radius_y=4)
        # self.image_viewer.apply_roi(different_roi)
        # assert self._subset_count() == (annulus_count + (2 if validity else 3))

    # ---------------------------------------------------------------------------
    # _is_rectangular_edit
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        ('delta_xmin', 'delta_xmax', 'delta_ymin', 'delta_ymax', 'validity'),
        [(-2, 2, -2, 2, True),  # resize same center
         (50, 50, 50, 50, True),  # move same size
         (50, 70, 50, 70, False)]  # new draw (move and resize)
    )
    def test_rectangle_resize_same_center(self, delta_xmin, delta_xmax, delta_ymin, delta_ymax,
                                          validity):
        # Test with zero size
        for xmax, ymax in ((0, 1), (1, 0)):
            old = RectangularROI(xmin=0, xmax=xmax, ymin=0, ymax=ymax)
            new = RectangularROI(xmin=old.xmin + delta_xmin,
                                 xmax=old.xmax + delta_xmax,
                                 ymin=old.ymin + delta_ymin,
                                 ymax=old.ymax + delta_ymax)
            assert not self.JVM._is_rectangular_edit(old, new)
            assert not self.JVM._is_roi_edit(self.JVM, old, new)

        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=old.xmin + delta_xmin,
                             xmax=old.xmax + delta_xmax,
                             ymin=old.ymin + delta_ymin,
                             ymax=old.ymax + delta_ymax)
        assert self.JVM._is_rectangular_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test in app behavior: resize, move, and new draw.
        # Draw initial roi and verify count
        # self.image_viewer.apply_roi(old)
        # assert self._subset_count() == 1
        #
        # self.image_viewer.apply_roi(new)
        # assert self._subset_count() == (1 if validity else 2)
        #
        # different_roi = RectangularROI(xmin=100, xmax=150, ymin=100, ymax=150)
        # self.image_viewer.apply_roi(different_roi)
        # assert self._subset_count() == (2 if validity else 3)

    # ---------------------------------------------------------------------------
    # _is_roi_edit  (dispatcher)
    # ---------------------------------------------------------------------------

    def test_roi_edit_different_types(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        assert not self.JVM._is_roi_edit(self.JVM, old, new)

    def test_roi_edit_unsupported_type(self):
        assert not self.JVM._is_roi_edit(self.JVM, object(), object())

    # ---------------------------------------------------------------------------
    # _is_range_edit
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ('delta_min', 'delta_max', 'validity'), [
            (2, 2, True),  # move, same width
            (5, 0, True),  # resize lo, same hi endpoint
            (0, 5, True),  # resize hi, same lo endpoint
            (50, 80, False)]  # new draw
    )
    def test_range_edits(self, delta_min, delta_max, validity):
        old_rss = RangeSubsetState(lo=10, hi=20)
        new_roi = XRangeROI(min=old_rss.lo + delta_min, max=old_rss.hi + delta_max)
        assert self.JVM._is_range_edit(old_rss, new_roi) == validity

        # Test in app behavior: resize, move, and new draw.
        # Draw initial roi and verify count
        # self.spectrum_viewer.apply_roi(old_rss)
        # assert self._subset_count() == 1
        #
        # self.spectrum_viewer.apply_roi(new_roi)
        # assert self._subset_count() == (1 if validity else 2)
        #
        # different_roi = XRangeROI(min=100, max=150)
        # self.spectrum_viewer.apply_roi(different_roi)
        # assert self._subset_count() == (2 if validity else 3)

    def test_range_no_min_max_attributes(self):
        rss = RangeSubsetState(lo=10, hi=20)
        assert not self.JVM._is_range_edit(object(), rss)
