import numpy as np
from astropy import units as u
from photutils.aperture import (CircularAperture, EllipticalAperture,
                                RectangularAperture)
from photutils.profiles import CurveOfGrowth, RadialProfile

from jdaviz.core.unit_conversion_utils import (flux_unit_conversion,
                                               is_unit_per_solid_angle)

__all__ = ['_curve_of_growth', '_radial_profile']


def _radial_profile(data, reg_bb, centroid, raw=False,
                    image_unit=None, display_unit=None, equivalencies=[], background=0):
    """Calculate radial profile.

    Parameters
    ----------
    data : ndarray or `~astropy.units.Quantity`
        Data for radial profile.

    reg_bb : obj
        Bounding box from ``ApertureStats``.

    centroid : tuple of int
        ``ApertureStats`` centroid or desired center in ``(x, y)``.

    raw : bool
        If `True`, returns raw data points for scatter plot.
        Otherwise, use ``imexam`` algorithm for a clean plot.

    image_unit : str or None
        Unit of input data, used with ``display_unit`` to convert output to
        the desired display unit.

    display_unit : str or None
        Desired unit for output.

    equivalencies : list or None
        Optional equivalencies for converting the radial profile to the
        selected display unit.

    background : float or `~astropy.units.Quantity`
        Background to subtract, if any. Unit must match ``data``.

    Returns
    -------
    x_arr, y_arr : ndarray
        X and Y data to plot. Y is already background-subtracted.
    """
    if isinstance(data, u.Quantity):
        data = data.value
    if isinstance(background, u.Quantity):
        background = background.value

    edge_radii = np.arange(max(reg_bb.shape) // 2 + 2)
    rp = RadialProfile(data, centroid, edge_radii, error=None, mask=None)

    if raw:
        x_arr = rp.data_radius
        y_arr = rp.data_profile - background
    else:
        x_arr = rp.radius
        y_arr = rp.profile - background

    if display_unit is not None:
        if image_unit is None:
            raise ValueError('Must provide image_unit with display_unit.')
        if image_unit != display_unit:
            y_arr = flux_unit_conversion(
                y_arr, u.Unit(image_unit), u.Unit(display_unit),
                equivalencies=equivalencies, with_unit=False)

    return x_arr, y_arr


def _curve_of_growth(data, centroid, aperture, wcs=None, background=0, n_datapoints=10,
                     pixarea_fac=None, image_unit=None, display_unit=None, equivalencies=[]):
    """Calculate curve of growth.

    Parameters
    ----------
    data : ndarray or `~astropy.units.Quantity`
        Data for the calculation.

    centroid : tuple of int
        ``ApertureStats`` centroid or desired center in ``(x, y)``.

    aperture : obj
        ``photutils`` aperture used to set radii for the curve. The actual
        aperture used is always circular.

    wcs : obj or `None`
        Supported WCS objects or `None`.

    background : float or `~astropy.units.Quantity`
        Background to subtract, if any. Unit must match ``data``.

    n_datapoints : int
        Number of data points in the curve.

    pixarea_fac : `~astropy.units.Quantity` or `None`
        For ``flux_unit/sr`` to ``flux_unit`` conversion.

    image_unit : str or None
        Unit of input data, used with ``display_unit`` to convert output to
        the desired display unit.

    display_unit : str or None
        Desired unit for output. If it is a surface brightness unit and
        ``pixarea_fac`` is provided, a flux unit is returned.

    equivalencies : list or None
        Optional equivalencies for converting the curve to the selected
        display unit.

    Returns
    -------
    x_arr : ndarray
        Data for the X-axis of the curve.

    sum_arr : ndarray or `~astropy.units.Quantity`
        Data for the Y-axis of the curve.

    x_label, y_label : str
        X- and Y-axis labels, respectively.

    Raises
    ------
    TypeError
        Unsupported aperture.
    """
    n_datapoints += 1

    if isinstance(data, u.Quantity):
        data = data.value
    if isinstance(background, u.Quantity):
        background = background.value

    if hasattr(aperture, 'to_pixel'):
        aperture = aperture.to_pixel(wcs)

    if isinstance(aperture, CircularAperture):
        r = aperture.r
    elif isinstance(aperture, EllipticalAperture):
        r = max(aperture.a, aperture.b)
    elif isinstance(aperture, RectangularAperture):
        r = max(aperture.w, aperture.h) * 0.5
    else:
        raise TypeError(f'Unsupported aperture: {aperture}')

    radii = np.linspace(0, r, num=n_datapoints)[1:]
    cog = CurveOfGrowth(data, centroid, radii, error=None, mask=None)
    x_arr = cog.radius
    sum_arr = cog.profile - (cog.radii ** 2 * np.pi * background)

    if image_unit is not None:
        sum_unit = u.Unit(image_unit)
        if (display_unit is not None) and (image_unit != display_unit):
            disp_unit = u.Unit(display_unit)
            do_flux_conv = True
        else:
            do_flux_conv = False

        if pixarea_fac is not None:
            sa = is_unit_per_solid_angle(sum_unit, return_unit=True)
            sum_unit *= sa
            sum_arr = sum_arr * pixarea_fac.value
            if do_flux_conv:
                disp_unit *= sa

        if do_flux_conv:
            converted_sum = flux_unit_conversion(
                sum_arr, sum_unit, disp_unit,
                equivalencies=equivalencies)
            sum_arr = converted_sum.value
            y_label = converted_sum.unit.to_string()
        else:
            y_label = sum_unit.to_string()
    else:
        y_label = 'Value'

    return x_arr, sum_arr, 'Radius (pix)', y_label
