"""The ``region_translators`` module houses translations of
:ref:`regions:shapes` to :ref:`photutils:photutils-aperture` apertures.
"""
from astropy import units as u
from astropy.coordinates import Angle
from photutils.aperture import (CircularAperture, SkyCircularAperture,
                                EllipticalAperture, SkyEllipticalAperture,
                                RectangularAperture, SkyRectangularAperture,
                                CircularAnnulus, SkyCircularAnnulus,
                                EllipticalAnnulus, SkyEllipticalAnnulus,
                                RectangularAnnulus, SkyRectangularAnnulus)
from regions import (CirclePixelRegion, CircleSkyRegion,
                     EllipsePixelRegion, EllipseSkyRegion,
                     RectanglePixelRegion, RectangleSkyRegion,
                     CircleAnnulusPixelRegion, CircleAnnulusSkyRegion,
                     EllipseAnnulusPixelRegion, EllipseAnnulusSkyRegion,
                     RectangleAnnulusPixelRegion, RectangleAnnulusSkyRegion, PixCoord)

__all__ = ['regions2aperture', 'aperture2regions']


def regions2aperture(region_shape):
    """Convert a given ``regions`` shape to ``photutils`` aperture.

    Parameters
    ----------
    region_shape : `regions.Region`
        A supported ``regions`` shape.

    Returns
    -------
    aperture : `photutils.aperture.Aperture`
        An equivalent ``photutils`` aperture.

    Raises
    ------
    NotImplementedError
        The given ``regions`` shape is not supported.

    Examples
    --------
    Translate a `regions.CirclePixelRegion` to `photutils.aperture.CircularAperture`:

    >>> from regions import CirclePixelRegion, PixCoord
    >>> from jdaviz.core.region_translators import regions2aperture
    >>> region_shape = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    >>> regions2aperture(region_shape)
    <CircularAperture([42., 43.], r=4.2)>

    See Also
    --------
    aperture2regions

    """
    if isinstance(region_shape, CirclePixelRegion):
        aperture = CircularAperture(region_shape.center.xy, region_shape.radius)

    elif isinstance(region_shape, CircleSkyRegion):
        aperture = SkyCircularAperture(region_shape.center, region_shape.radius)

    elif isinstance(region_shape, EllipsePixelRegion):
        aperture = EllipticalAperture(
            region_shape.center.xy, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, EllipseSkyRegion):
        aperture = SkyEllipticalAperture(
            region_shape.center, region_shape.width * 0.5, region_shape.height * 0.5,
            theta=region_shape.angle)

    elif isinstance(region_shape, RectanglePixelRegion):
        aperture = RectangularAperture(
            region_shape.center.xy, region_shape.width, region_shape.height,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, RectangleSkyRegion):
        aperture = SkyRectangularAperture(
            region_shape.center, region_shape.width, region_shape.height, theta=region_shape.angle)

    elif isinstance(region_shape, CircleAnnulusPixelRegion):
        aperture = CircularAnnulus(
            region_shape.center.xy, region_shape.inner_radius, region_shape.outer_radius)

    elif isinstance(region_shape, CircleAnnulusSkyRegion):
        aperture = SkyCircularAnnulus(
            region_shape.center, region_shape.inner_radius, region_shape.outer_radius)

    elif isinstance(region_shape, EllipseAnnulusPixelRegion):
        aperture = EllipticalAnnulus(
            region_shape.center.xy, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, EllipseAnnulusSkyRegion):
        aperture = SkyEllipticalAnnulus(
            region_shape.center, region_shape.inner_width * 0.5, region_shape.outer_width * 0.5,
            region_shape.outer_height * 0.5, b_in=region_shape.inner_height * 0.5,
            theta=region_shape.angle)

    elif isinstance(region_shape, RectangleAnnulusPixelRegion):
        aperture = RectangularAnnulus(
            region_shape.center.xy, region_shape.inner_width, region_shape.outer_width,
            region_shape.outer_height, h_in=region_shape.inner_height,
            theta=region_shape.angle.to_value(u.radian))

    elif isinstance(region_shape, RectangleAnnulusSkyRegion):
        aperture = SkyRectangularAnnulus(
            region_shape.center, region_shape.inner_width, region_shape.outer_width,
            region_shape.outer_height, h_in=region_shape.inner_height, theta=region_shape.angle)

    else:
        raise NotImplementedError(f'{region_shape.__class__.__name__} is not supported')

    return aperture


def aperture2regions(aperture):
    """Convert a given ``photutils`` aperture to ``regions`` shape.

    Parameters
    ----------
    aperture : `photutils.aperture.Aperture`
        An equivalent ``photutils`` aperture.

    Returns
    -------
    region_shape : `regions.Region`
        A supported ``regions`` shape.

    Raises
    ------
    NotImplementedError
        The given ``photutils`` aperture is not supported.

    ValueError
        Invalid inputs.

    Examples
    --------
    Translate a `photutils.aperture.CircularAperture` to `regions.CirclePixelRegion`:

    >>> from photutils import CircularAperture
    >>> from jdaviz.core.region_translators import aperture2regions
    >>> aperture = CircularAperture((42, 43), 4.2)
    >>> aperture2regions(aperture)
    <CirclePixelRegion(center=PixCoord(x=42.0, y=43.0), radius=4.2)>

    See Also
    --------
    regions2aperture

    """
    if isinstance(aperture, CircularAperture):
        region_shape = CirclePixelRegion(
            center=positions2pixcoord(aperture.positions), radius=aperture.r)

    elif isinstance(aperture, SkyCircularAperture):
        region_shape = CircleSkyRegion(center=aperture.positions, radius=aperture.r)

    elif isinstance(aperture, EllipticalAperture):
        region_shape = EllipsePixelRegion(
            center=positions2pixcoord(aperture.positions), width=aperture.a * 2,
            height=aperture.b * 2, angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyEllipticalAperture):
        region_shape = EllipseSkyRegion(
            center=aperture.positions, width=aperture.a * 2, height=aperture.b * 2,
            angle=aperture.theta)

    elif isinstance(aperture, RectangularAperture):
        region_shape = RectanglePixelRegion(
            center=positions2pixcoord(aperture.positions), width=aperture.w, height=aperture.h,
            angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyRectangularAperture):
        region_shape = RectangleSkyRegion(
            center=aperture.positions, width=aperture.w, height=aperture.h, angle=aperture.theta)

    elif isinstance(aperture, CircularAnnulus):
        region_shape = CircleAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_radius=aperture.r_in,
            outer_radius=aperture.r_out)

    elif isinstance(aperture, SkyCircularAnnulus):
        region_shape = CircleAnnulusSkyRegion(
            center=aperture.positions, inner_radius=aperture.r_in, outer_radius=aperture.r_out)

    elif isinstance(aperture, EllipticalAnnulus):
        region_shape = EllipseAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_width=aperture.a_in * 2,
            inner_height=aperture.b_in * 2, outer_width=aperture.a_out * 2,
            outer_height=aperture.b_out * 2, angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyEllipticalAnnulus):
        region_shape = EllipseAnnulusSkyRegion(
            center=aperture.positions, inner_width=aperture.a_in * 2,
            inner_height=aperture.b_in * 2, outer_width=aperture.a_out * 2,
            outer_height=aperture.b_out * 2, angle=aperture.theta)

    elif isinstance(aperture, RectangularAnnulus):
        region_shape = RectangleAnnulusPixelRegion(
            center=positions2pixcoord(aperture.positions), inner_width=aperture.w_in,
            inner_height=aperture.h_in, outer_width=aperture.w_out, outer_height=aperture.h_out,
            angle=theta2angle(aperture.theta))

    elif isinstance(aperture, SkyRectangularAnnulus):
        region_shape = RectangleAnnulusSkyRegion(
            center=aperture.positions, inner_width=aperture.w_in, inner_height=aperture.h_in,
            outer_width=aperture.w_out, outer_height=aperture.h_out, angle=aperture.theta)

    else:  # pragma: no cover
        raise NotImplementedError(f'{aperture.__class__.__name__} is not supported')

    return region_shape


def positions2pixcoord(positions):
    """Convert ``photutils`` aperture positions to `~regions.PixCoord`
    that is acceptable by ``regions`` shape.
    """
    if positions.shape != (2, ):
        raise ValueError('regions shape only accepts scalar x and y positions')
    if isinstance(positions, u.Quantity):
        pixcoord = PixCoord(x=positions[0].value, y=positions[1].value)
    else:
        pixcoord = PixCoord(x=positions[0], y=positions[1])
    return pixcoord


def theta2angle(theta):
    """Convert ``photutils`` theta to ``regions`` angle."""
    return Angle(theta, u.radian)
