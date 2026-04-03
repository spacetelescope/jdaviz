"""
Tests for JdavizViewerMixin ROI edit-detection helpers and the
``apply_roi`` override that lets users resize/move subsets in-place
in the deconfigged configuration.
"""

import warnings

import pytest
from glue.core.roi import (CircularAnnulusROI,
                           CircularROI,
                           EllipticalROI,
                           RectangularROI,
                           XRangeROI)
from glue.core.subset import RangeSubsetState
from glue_jupyter.bqplot.common.tools import TrueCircularROI

from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin


class TestROIEdits:
    """
    Unit tests for all types of ROI edits as well as
    app testing.
    """

    @staticmethod
    def _subset_count(app):
        return len(app.plugins['Subset Tools'].get_regions())

    # ---------------------------------------------------------------------------
    # _is_circular_edit
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        ('delta_xc', 'delta_yc', 'delta_r', 'validity'),
        # validity is 'move', 'resize', or None (new draw).
        [(0, 0, 3, 'resize'),   # same center, radius changed → resize
         (2, 0, 3, None),       # center moved, radius changed → new draw
         (40, 40, 0, 'move'),   # same radius, center moved far → move
         (40, 40, 3, None)]     # center moved far and radius changed → new draw
    )
    def test_circular_roi_edit(self, delta_xc, delta_yc, delta_r, validity,
                               deconfigged_helper, image_hdu_wcs):

        # Zero initial radius: always None (any change is a new draw).
        old = CircularROI(xc=10, yc=10, radius=0)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert JdavizViewerMixin._is_circular_edit(old, new) is None
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) is None

        # Check subclass.
        old = TrueCircularROI(xc=10, yc=10, radius=5)
        new = TrueCircularROI(xc=old.xc + delta_xc,
                              yc=old.yc + delta_yc,
                              radius=old.radius + delta_r)
        assert JdavizViewerMixin._is_circular_edit(old, new) == validity
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) == validity

        # Check parent class and use for the app testing.
        old = CircularROI(xc=10, yc=10, radius=5)
        new = CircularROI(xc=old.xc + delta_xc, yc=old.yc + delta_yc, radius=old.radius + delta_r)
        assert JdavizViewerMixin._is_circular_edit(old, new) == validity
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) == validity

        # Test in app behavior: resize, move, and new draw.
        deconfigged_helper.load(image_hdu_wcs, format='Image')
        image_viewer = deconfigged_helper.app.get_viewer('Image')

        # Draw initial roi and verify count.
        image_viewer.apply_roi(old)
        assert self._subset_count(deconfigged_helper) == 1

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            image_viewer.apply_roi(new)
        assert self._subset_count(deconfigged_helper) == (1 if validity is not None else 2)

        different_roi = CircularROI(xc=100, yc=100, radius=2)
        image_viewer.apply_roi(different_roi)
        assert self._subset_count(deconfigged_helper) == (2 if validity is not None else 3)

    def test_circular_small_move_radius_drift(self):
        """
        A small center move paired with a slight radius drift must not create a
        new subset. Because the center barely moved the operation is caught as
        'resize', not None.
        """
        old = CircularROI(xc=10, yc=10, radius=5)

        # 1 % radius drift + tiny center movement → caught as resize.
        result = JdavizViewerMixin._is_circular_edit(
            old, CircularROI(xc=10.1, yc=10, radius=5 * 1.01))
        assert result == 'resize'

        # Drift within rtol=1e-3 → still a move.
        result2 = JdavizViewerMixin._is_circular_edit(
            old, CircularROI(xc=10.5, yc=10, radius=5 * (1 + 5e-4)))
        assert result2 == 'move'

        # Large center movement with radius change → new draw.
        result3 = JdavizViewerMixin._is_circular_edit(
            old, CircularROI(xc=old.xc + 3.0, yc=old.yc, radius=old.radius + 1.0))
        assert result3 is None

        # All results must be valid, never anything unexpected.
        for dx in (0.1, 1.0, 3.0, 4.9):
            for dr in (0.0, 0.1, 1.0, 3.0):
                result = JdavizViewerMixin._is_circular_edit(
                    old,
                    CircularROI(xc=old.xc + dx, yc=old.yc, radius=old.radius + dr)
                )
                assert result in ('move', 'resize', None), \
                    f'Unexpected result {result!r} for dx={dx}, dr={dr}'

    # ---------------------------------------------------------------------------
    # _is_annulus_edit AND _is_elliptical_edit
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        ('delta_xc', 'delta_yc', 'delta_ixr', 'delta_oyr', 'validity'),
        [(0, 0, 1, 2, 'resize'),   # same center, radii changed → resize
         (40, 40, 0, 0, 'move'),   # same radii, center moved far → move
         (40, 40, 2, 4, None),     # center moved far + radii changed → new draw
         (40, 40, 1, 0, None),     # center moved far + inner/x radius changed → new draw
         (40, 40, 0, 2, None)]     # center moved far + outer/y radius changed → new draw
    )
    def test_annulus_elliptical_roi_edit(self, delta_xc, delta_yc, delta_ixr, delta_oyr, validity):
        # Invalid initial outer radius: always None.
        for old_ir, old_or in ((0, 0), (1, 0)):
            old = CircularAnnulusROI(xc=10, yc=10, inner_radius=old_ir, outer_radius=old_or)
            new = CircularAnnulusROI(xc=old.xc + delta_xc,
                                     yc=old.yc + delta_yc,
                                     inner_radius=old.inner_radius + delta_ixr,
                                     outer_radius=old.outer_radius + delta_oyr)
            assert JdavizViewerMixin._is_annulus_edit(old, new) is None
            assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) is None

        # Valid initial parameters.
        old = CircularAnnulusROI(xc=10, yc=10, inner_radius=3, outer_radius=6)
        new = CircularAnnulusROI(xc=old.xc + delta_xc,
                                 yc=old.yc + delta_yc,
                                 inner_radius=old.inner_radius + delta_ixr,
                                 outer_radius=old.outer_radius + delta_oyr)
        assert JdavizViewerMixin._is_annulus_edit(old, new) == validity
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) == validity

        # ---------------------------------------------------------------------------
        # _is_elliptical_edit
        # ---------------------------------------------------------------------------
        # Invalid (zero) initial x/y radius: always None.
        for i, j in ((0, 1), (1, 0)):
            old = EllipticalROI(xc=10, yc=10, radius_x=i, radius_y=j)
            new = EllipticalROI(xc=old.xc + delta_xc,
                                yc=old.yc + delta_yc,
                                radius_x=old.radius_x + delta_ixr,
                                radius_y=old.radius_y + delta_oyr)
            assert JdavizViewerMixin._is_elliptical_edit(old, new) is None
            assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) is None

        # Valid initial parameters.
        old = EllipticalROI(xc=10, yc=10, radius_x=3, radius_y=6)
        new = EllipticalROI(xc=old.xc + delta_xc,
                            yc=old.yc + delta_yc,
                            radius_x=old.radius_x + delta_ixr,
                            radius_y=old.radius_y + delta_oyr)
        assert JdavizViewerMixin._is_elliptical_edit(old, new) == validity
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) == validity

    # ---------------------------------------------------------------------------
    # _is_rectangular_edit
    # ---------------------------------------------------------------------------
    @pytest.mark.parametrize(
        ('delta_xmin', 'delta_xmax', 'delta_ymin', 'delta_ymax', 'validity'),
        [(-2, 2, -2, 2, 'resize'),   # same center (dist=0), dims changed → resize
         (50, 50, 50, 50, 'move'),   # same dims, center moved far → move
         (50, 70, 50, 70, None)]     # dims changed + center far → new draw
    )
    def test_rectangle_resize_same_center(self, delta_xmin, delta_xmax, delta_ymin, delta_ymax,
                                          validity):
        # Zero-size rect: always None.
        for xmax, ymax in ((0, 1), (1, 0)):
            old = RectangularROI(xmin=0, xmax=xmax, ymin=0, ymax=ymax)
            new = RectangularROI(xmin=old.xmin + delta_xmin,
                                 xmax=old.xmax + delta_xmax,
                                 ymin=old.ymin + delta_ymin,
                                 ymax=old.ymax + delta_ymax)
            assert JdavizViewerMixin._is_rectangular_edit(old, new) is None
            assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) is None

        # Valid initial parameters.
        old = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        new = RectangularROI(xmin=old.xmin + delta_xmin,
                             xmax=old.xmax + delta_xmax,
                             ymin=old.ymin + delta_ymin,
                             ymax=old.ymax + delta_ymax)
        assert JdavizViewerMixin._is_rectangular_edit(old, new) == validity
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) == validity

    # ---------------------------------------------------------------------------
    # _is_roi_edit None cases
    # ---------------------------------------------------------------------------

    def test_roi_edit_different_types(self):
        old = CircularROI(xc=10, yc=10, radius=5)
        new = RectangularROI(xmin=0, xmax=10, ymin=0, ymax=10)
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, old, new) is None

    def test_roi_edit_unsupported_type(self):
        assert JdavizViewerMixin._is_roi_edit(JdavizViewerMixin, object(), object()) is None

    # ---------------------------------------------------------------------------
    # _is_range_edit
    # ---------------------------------------------------------------------------

    @pytest.mark.parametrize(
        ('delta_min', 'delta_max', 'validity'), [
            (2, 2, 'move'),     # same width → move
            (5, 0, 'resize'),   # lo moved, hi fixed → resize
            (0, 5, 'resize'),   # hi moved, lo fixed → resize
            (50, 80, None)]     # neither endpoint fixed → new draw
    )
    def test_range_edits(self, delta_min, delta_max, validity,
                         deconfigged_helper, spectrum1d):
        old_rss = RangeSubsetState(lo=10, hi=20)
        new_roi = XRangeROI(min=old_rss.lo + delta_min, max=old_rss.hi + delta_max)
        assert JdavizViewerMixin._is_range_edit(old_rss, new_roi) == validity

        # Test in app behavior: resize, move, and new draw.
        deconfigged_helper.load(spectrum1d, format='1D Spectrum')
        spectrum_viewer = deconfigged_helper.app.get_viewer('1D Spectrum')

        # Draw initial roi and verify count.
        initial_roi = XRangeROI(min=old_rss.lo, max=old_rss.hi)
        spectrum_viewer.apply_roi(initial_roi)
        assert self._subset_count(deconfigged_helper) == 1

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            spectrum_viewer.apply_roi(new_roi)
        assert self._subset_count(deconfigged_helper) == (1 if validity is not None else 2)

        different_roi = XRangeROI(min=100, max=150)
        spectrum_viewer.apply_roi(different_roi)
        assert self._subset_count(deconfigged_helper) == (2 if validity is not None else 3)

    def test_range_no_min_max_attributes(self):
        rss = RangeSubsetState(lo=10, hi=20)
        assert JdavizViewerMixin._is_range_edit(rss, object()) is None
