"""
Tests for JdavizViewerMixin ROI edit-detection helpers and the
``apply_roi`` override that lets users resize/move subsets in-place
in the deconfigged configuration.
"""

import numpy as np
import pytest
from astropy.nddata import NDData
from glue.core.edit_subset_mode import NewMode
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
    Tests for all types of ROI edits.
    """

    @pytest.fixture(autouse=True)
    def setup_class(self):
        self.JVM = JdavizViewerMixin

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
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert self.JVM._is_circular_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test with zero initial radius, always False since any change would be a new draw
        old = CircularROI(xc=10, yc=10, radius=0)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert not self.JVM._is_circular_edit(old, new)
        assert not self.JVM._is_roi_edit(self.JVM, old, new)

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
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=old.xc + delta_xc,
                                 yc=old.yc + delta_yc,
                                 inner_radius=old.inner_radius + delta_ixr,
                                 outer_radius=old.outer_radius + delta_oyr)
        assert self.JVM._is_annulus_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

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

        # ---------------------------------------------------------------------------
        # _is_elliptical_edit
        # ---------------------------------------------------------------------------

        old = EllipticalROI(xc=10, yc=10, radius_x=3, radius_y=6)
        new = EllipticalROI(xc=old.xc + delta_xc,
                            yc=old.yc + delta_yc,
                            radius_x=old.radius_x + delta_ixr,
                            radius_y=old.radius_y + delta_oyr)
        assert self.JVM._is_elliptical_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test with zero initial x/y radius
        for i, j in ((0, 1), (1, 0)):
            old = EllipticalROI(xc=10, yc=10, radius_x=i, radius_y=j)
            new = EllipticalROI(xc=old.xc + delta_xc,
                                yc=old.yc + delta_yc,
                                radius_x=old.radius_x + delta_ixr,
                                radius_y=old.radius_y + delta_oyr)
            assert not self.JVM._is_elliptical_edit(old, new)
            assert not self.JVM._is_roi_edit(self.JVM, old, new)

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
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=old.xmin + delta_xmin,
                             xmax=old.xmax + delta_xmax,
                             ymin=old.ymin + delta_ymin,
                             ymax=old.ymax + delta_ymax)
        assert self.JVM._is_rectangular_edit(old, new) == validity
        assert self.JVM._is_roi_edit(self.JVM, old, new) == validity

        # Test with zero size
        for xmax, ymax in ((0, 1), (1, 0)):
            old = RectangularROI(xmin=0, xmax=xmax, ymin=0, ymax=ymax)
            new = RectangularROI(xmin=old.xmin + delta_xmin,
                                 xmax=old.xmax + delta_xmax,
                                 ymin=old.ymin + delta_ymin,
                                 ymax=old.ymax + delta_ymax)
            assert not self.JVM._is_rectangular_edit(old, new)
            assert not self.JVM._is_roi_edit(self.JVM, old, new)

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
        new_roi = XRangeROI(old_rss.lo + delta_min, old_rss.hi + delta_max)
        assert self.JVM._is_range_edit(old_rss, new_roi) == validity

    def test_range_no_min_max_attributes(self):
        rss = RangeSubsetState(lo=10, hi=20)
        assert not self.JVM._is_range_edit(object(), rss)

# ---------------------------------------------------------------------------
# Programmatic test: apply_roi in deconfigged
# ---------------------------------------------------------------------------


class TestDeconfiggedSubsetEditInPlace:
    """
    End-to-end test verifying that resize and move operations in
    deconfigged modify subsets in-place, while new draws create
    new subsets.
    """

    @pytest.fixture(autouse=True)
    def setup_method(self, deconfigged_helper, image_2d_wcs):
        """
        Set up deconfigged app with a 100x100 image.
        """
        arr = np.ones((100, 100))
        ndd = NDData(arr, wcs=image_2d_wcs)
        deconfigged_helper.load(ndd, data_label='test_image')
        self.app = deconfigged_helper
        self.viewer = list(
            deconfigged_helper.app.get_viewers_of_cls('ImvizImageView')
        )[0]

    def _subset_count(self):
        return len(self.app.app.data_collection.subset_groups)

    def _active_subset_state(self):
        esm = self.viewer.session.edit_subset_mode
        if esm.edit_subset:
            return esm.edit_subset[0].subset_state
        return None

    def test_draw_creates_new_subset(self):
        """
        Drawing a circle should create a new subset.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        assert self._subset_count() == 1

    def test_resize_modifies_in_place(self):
        """
        Resizing (same center, different radius) should modify
        the existing subset rather than creating a second one.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=15))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.radius, 15)

    def test_move_modifies_in_place(self):
        """
        Moving (same radius, different center) should modify
        the existing subset rather than creating a second one.
        """
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=60, yc=55, radius=10))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.xc, 60)

    def test_new_draw_elsewhere_creates_second_subset(self):
        """
        Drawing a differently sized region far away should create
        a new subset, not modify the existing one.
        """
        self.viewer.apply_roi(CircularROI(xc=20, yc=20, radius=5))
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=12))
        assert self._subset_count() == 2

    def test_annulus_resize_in_place(self):
        """
        Resizing an annulus should modify it in-place (regression
        for the center-in-hole bug).
        """
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=5, outer_radius=10)
        )
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=7, outer_radius=14)
        )
        assert self._subset_count() == 1

    def test_annulus_move_in_place(self):
        """
        Moving an annulus should modify it in-place.
        """
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=50, yc=50, inner_radius=5, outer_radius=10)
        )
        self.viewer.apply_roi(
            CircularAnnulusROI(xc=60, yc=55, inner_radius=5, outer_radius=10)
        )
        assert self._subset_count() == 1

    def test_rectangle_resize_in_place(self):
        """
        Resizing a rectangle should modify it in-place.
        """
        self.viewer.apply_roi(RectangularROI(xmin=40, xmax=60, ymin=40, ymax=60))
        self.viewer.apply_roi(RectangularROI(xmin=35, xmax=65, ymin=35, ymax=65))
        assert self._subset_count() == 1

    def test_rectangle_move_in_place(self):
        """
        Moving a rectangle should modify it in-place.
        """
        self.viewer.apply_roi(RectangularROI(xmin=40, xmax=60, ymin=40, ymax=60))
        self.viewer.apply_roi(RectangularROI(xmin=50, xmax=70, ymin=50, ymax=70))
        assert self._subset_count() == 1

    def test_mode_restored_after_override(self):
        """
        After an in-place edit the mode should remain NewMode so
        that subsequent new draws still create new subsets.
        """
        esm = self.viewer.session.edit_subset_mode
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(CircularROI(xc=50, yc=50, radius=15))
        assert esm.mode is NewMode

    def test_multiple_subsets_then_edit(self):
        """
        Create two subsets, then resize the second; only the
        second should be modified.
        """
        self.viewer.apply_roi(CircularROI(xc=20, yc=20, radius=5))
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=12))
        assert self._subset_count() == 2
        self.viewer.apply_roi(CircularROI(xc=80, yc=80, radius=18))
        assert self._subset_count() == 2

    def test_true_circular_resize_in_place(self):
        """
        TrueCircularROI (from bqplot:truecircle) should resize
        in-place just like CircularROI.
        """
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=15))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.radius, 15)

    def test_true_circular_move_in_place(self):
        """
        TrueCircularROI (from bqplot:truecircle) should move
        in-place just like CircularROI.
        """
        self.viewer.apply_roi(TrueCircularROI(xc=50, yc=50, radius=10))
        self.viewer.apply_roi(TrueCircularROI(xc=60, yc=55, radius=10))
        assert self._subset_count() == 1
        assert np.isclose(self._active_subset_state().roi.xc, 60)
